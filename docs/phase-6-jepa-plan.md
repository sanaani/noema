# Phase 6 (queued) — JEPA-style conjecture placement

Queued 2026-09-25, to run after phase 5 closes. Not yet pre-registered.

- **Map:** encoder B from phase 4, frozen. Only a predictor is trained, which
  avoids JEPA's collapse failure.
- **Predictor:** input is the map positions of the lemmas a theorem cites;
  output is the predicted position of the theorem's statement.
- **Training data:** every theorem in 2024 Mathlib (~200,000) with its 2024
  dependencies. No 2026 data.
- **Test:** for each 2026 connector, predict its position from the corpus
  theorems it cites; score against its actual 2026 statement position, compared
  with the plain average of the cited lemmas' positions.
- **Needs:** 2024 statements printed for all of Mathlib (one AWS print job with
  Lean 4.9 / Mathlib `f0957a7`) and encoded with B. A few dollars.
- **Out of scope:** writing statements or proving them.
