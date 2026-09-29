# Noema: rules for agents

- Lint with `scripts/lint.sh` (it finds `.venv/bin/ruff`; plain `ruff` is not
  on PATH here). `scripts/lint.sh --fix` formats and fixes. CI runs the same
  script, so if it passes locally, lint passes in CI.
- Git hooks live in `.githooks` (`git config core.hooksPath .githooks`):
  pre-commit lints and pre-push runs pytest. Never bypass them with `--no-verify`.
- After every push, confirm CI with `gh run list --limit 1`. A red run is
  fixed before any other work.
- Do not use `# fmt: skip` to keep long lines; line length is 100.
