"""Phase 14: matching a tool to a bibliography entry and pulling its citation contexts."""

import gzip
import importlib.util
import io
import tarfile
from pathlib import Path

import pytest

pytest.importorskip("sklearn")
ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("p14", ROOT / "scripts/run-phase14.py")
p14 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p14)

TEX = r"""
\section{Introduction}
Background can be found in \cite{HJ, other}. % a comment \cite{HJ}
\section{Proof of the main theorem}
By the Weyl inequality \cite[Thm 4.3.1]{HJ}, the eigenvalues satisfy the bound.
\begin{thebibliography}{9}
\bibitem{HJ} R.~A. Horn and C.~R. Johnson, \emph{Matrix Analysis}, Cambridge, 1985.
\bibitem{other} J.~Smith, Matrix theory of analysis, 2001.
\end{thebibliography}
"""


def tarball(files):
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as tf:
        for name, text in files.items():
            data = text.encode()
            info = tarfile.TarInfo(name)
            info.size = len(data)
            tf.addfile(info, io.BytesIO(data))
    return gzip.compress(buf.getvalue())


def test_match_needs_surname_and_title_words():
    tw, sn = p14.title_words("Matrix Analysis"), p14.words("Horn")
    assert p14.matches(r"R.~A. Horn and C.~R. Johnson, \emph{Matrix Analysis}", tw, sn)
    assert not p14.matches("J. Smith, Matrix theory of analysis", tw, sn)
    assert not p14.matches("R. Horn, Topics in Matrix theory", tw, sn)


def test_contexts_from_tarball_skip_comments_and_keep_sections():
    body, bib = p14.unpack(tarball({"main.tex": TEX}))
    tw, sn = p14.title_words("Matrix Analysis"), p14.words("Horn")
    keys = {k for k, e in p14.bib_entries(body, bib) if p14.matches(e, tw, sn)}
    assert keys == {"HJ"}
    ctx = p14.contexts(body, keys)
    assert [c["section"] for c in ctx] == ["Introduction", "Proof of the main theorem"]


def test_pdf_only_and_single_file_sources():
    assert p14.unpack(b"%PDF-1.5 ...") is None
    body, _ = p14.unpack(gzip.compress(TEX.encode()))
    assert "Weyl inequality" in body
