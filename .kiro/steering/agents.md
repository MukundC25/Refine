---
inclusion: always
---

# Coding Standards — Refine × Redrob Ranking System

## Project layout

```
backend/app/core/       — pure Python scoring components (no FastAPI deps)
backend/app/routers/    — FastAPI routers that call core components
backend/app/models/     — Pydantic schemas for the API layer
backend/tests/          — pytest tests, one file per core module
conftest.py             — sys.path setup only, nothing else
```

## Language and runtime

- Python 3.11+. Use `match` statements, walrus operator, `X | Y` union types freely.
- All new core files use `from __future__ import annotations`.
- Use `TYPE_CHECKING` guards for imports that would create circular dependencies.

## Code style

- No section separator comments (`# ─────`, `# ==`, `# --`).
- No `Args:` / `Returns:` / `Raises:` docstring blocks. Write one-line docstrings or skip entirely if the function name is self-explanatory.
- No `# Implementation: Issue NNN` tags inside source files.
- Inline comments only when the logic is non-obvious — not to restate what the code does.
- Constants in UPPER_CASE at module level as `frozenset` or `list`. Group related constants together without visual separators.
- Prefer `dataclass` for result types (consistent with `RuleScore`, `HoneypotResult`).
- Functions over classes unless state is genuinely needed.
- Keep files focused — one responsibility per file.

## Imports

- Standard library first, then third-party, then local — blank line between groups.
- No wildcard imports.
- Lazy-import heavy dependencies (torch, sentence-transformers) inside functions or `__init__` to keep module-level import cost low.

## Data models

- `CandidateRecord` and all sub-models live in `candidate_loader.py`.
- `ParsedJD` lives in `jd_parser.py` as a dataclass.
- `RuleScore`, `HoneypotResult`, and new result types are plain `@dataclass` in their own module.
- Pydantic `BaseModel` subclasses live in `schemas.py` — only for API request/response shapes.

## Scoring conventions

- All score functions return a plain `float`. No side effects.
- Scores are always deterministic — same input always produces same output.
- Every component score is bounded and documented in the module docstring.
- `total` fields are always clamped: `max(0.0, raw_sum)`.
- Penalty values are either `0.0` (clean) or a fixed negative (`-50.0`), never arbitrary floats.

## Testing

- One test file per core module: `test_<module>.py` in `backend/tests/`.
- Fixtures: `sample_raw` (raw JSON list), `sample_records` (validated), `senior_ai_jd` / `empty_jd`.
- Sample data path: `pathlib.Path(__file__).resolve().parents[3] / "[PUB] India_runs_data_and_ai_challenge" / "India_runs_data_and_ai_challenge" / "sample_candidates.json"`.
- No section separator comments in test files either.
- Test class per function group: `TestFunctionName`.
- Helper functions `_get(raw, cid)` and `_clone(raw, cid, **overrides)` for building mutated records.
- No lengthy docstrings on test methods — the test name should be self-explanatory. Add a one-liner comment only if the "why" is non-obvious.
- Performance tests go in `TestPerformance` at the bottom.
- Edge cases go in `TestEdgeCases` at the bottom.

## Git workflow

- Branch per issue: `issue-NNN-<short-description>`.
- Never push to `main` directly.
- Stage only files that belong in the repo — never `.venv*/`, `docs/`, `precomputed/`, `*.npy`, `candidates.jsonl`, `submission.csv`, `logs/`.
- `docs/` is gitignored — issue markdown files stay local.
- Commit message: `Issue NNN: <imperative sentence>\n\n- bullet list of what changed`.

## What stays local (gitignored)

```
docs/           issue specs and audit files
.venv*/         all virtual environments
precomputed/    embeddings .npy files and candidate_ids.json
candidates.jsonl / candidates.jsonl.gz
submission.csv
logs/
notebooks/
```
