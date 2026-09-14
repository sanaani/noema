# Structurally matched strategy-transfer archive

Completed conditional development study: headroom passes, power qualifies 512
confirmation triplets, and the cloud stability gate fails with 0/100 qualifying
draws (80 required). No confirmation corpus was acquired under that protocol.
The user subsequently removed the 10-point continuation requirement; the fresh
confirmation is recorded separately and does not alter these historical results.

- `development-plan.json.gz`: the frozen 64 triplets and complete shortest-program banks.
- `assignment-freeze.json`: preregistered source and input hashes.
- `headroom/`: nine controls, 24 Lean proof fixtures, raw states and initial vectors.
- `power/`: 90,000 simulated experiments and 810,000 paired comparisons.
- `geometry/`: initial cloud results, every resampling draw and expanded vectors.
- `validation.json`: archive reconstruction, including all 100 proof samples.
- `figures/`: plots exported as PNG and PDF.
- `SHA256SUMS`: checksums for every other file in this archive.

Read `docs/strategy-transfer-results-v2.md` and
`docs/reproduction-strategy-transfer-v2.md` from the repository root for the
scientific scope, registered decisions and executable reproduction commands.
Run `sha256sum -c SHA256SUMS` inside this directory to check archive integrity.
Model weights and Lean binaries are unnecessary for the archive-only verifier.
