import json
import runpy
import signal
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest


@pytest.mark.parametrize("foreign_pid", [False, True])
def test_scheduler_resumes_on_failure_and_never_signals_foreign_pid(
    tmp_path, monkeypatch, foreign_pid
):
    run = tmp_path / "run"
    (run / "workers").mkdir(parents=True)
    script = Path(__file__).resolve().parents[1] / "scripts/serialize-confirmation-encoding.py"
    main = runpy.run_path(str(script))["main"]
    monkeypatch.setattr(
        sys, "argv", [str(script), "--run", str(run), "--active-pid", "11", "--waiting-pid", "12"]
    )
    read_bytes = Path.read_bytes

    def process_command(path):
        if str(path) not in ("/proc/11/cmdline", "/proc/12/cmdline"):
            return read_bytes(path)
        if foreign_pid and str(path) == "/proc/12/cmdline":
            return b"python\x00unrelated.py\x00"
        shard = "0" if str(path) == "/proc/11/cmdline" else "1"
        return "\0".join(
            [
                "python",
                "scripts/confirmation-acquisition-worker.py",
                "encode",
                "--run",
                str(run),
                "--shard",
                shard,
                "",
            ]
        ).encode()

    monkeypatch.setattr(Path, "read_bytes", process_command)
    calls = []
    main.__globals__["os"] = SimpleNamespace(kill=lambda pid, sig: calls.append((pid, sig)))
    main.__globals__["signal"] = SimpleNamespace(
        SIGTERM=signal.SIGTERM,
        SIGSTOP=signal.SIGSTOP,
        SIGCONT=signal.SIGCONT,
        signal=lambda *args: None,
    )

    def interrupt(seconds):
        raise RuntimeError("simulated scheduler failure")

    main.__globals__["time"] = SimpleNamespace(monotonic=lambda: 0, sleep=interrupt)
    if foreign_pid:
        with pytest.raises(ValueError, match="PIDs must identify"):
            main()
        assert not calls
    else:
        with pytest.raises(RuntimeError, match="simulated scheduler failure"):
            main()
        assert calls == [(12, signal.SIGSTOP), (12, signal.SIGCONT)]
        assert (
            json.loads((run / "workers/serial-scheduling.json").read_text())["state"]
            == "second_shard_resumed"
        )
