#!/usr/bin/env python3
"""spot_check.py — Quick sanity-check of a submission.csv before portal upload.

Usage:
    python scripts/spot_check.py [path/to/submission.csv]

Defaults to ./submission.csv when no path is given.

Exits 0 if all checks pass, 1 if any check fails.
"""

import csv
import re
import sys
from pathlib import Path

CANDIDATE_ID_RE = re.compile(r"^CAND_[0-9]{7}$")
NON_TECHNICAL_TITLES = {
    "marketing manager", "hr manager", "accountant", "sales manager",
    "operations manager", "graphic designer", "content writer", "civil engineer",
    "mechanical engineer", "customer support", "hr", "recruiter",
}


def load_rows(path: str) -> list[dict]:
    with open(path, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def check_structure(rows: list[dict]) -> list[str]:
    errors = []
    required_header = {"candidate_id", "rank", "score", "reasoning"}
    if not rows:
        return ["CSV is empty"]
    if set(rows[0].keys()) != required_header:
        errors.append(f"Wrong columns: {set(rows[0].keys())} — expected {required_header}")
    if len(rows) != 100:
        errors.append(f"Expected 100 rows, got {len(rows)}")
    return errors


def check_ids(rows: list[dict]) -> list[str]:
    errors = []
    seen = set()
    for r in rows:
        cid = r["candidate_id"].strip()
        if not CANDIDATE_ID_RE.match(cid):
            errors.append(f"Invalid candidate_id: {cid!r}")
        if cid in seen:
            errors.append(f"Duplicate candidate_id: {cid!r}")
        seen.add(cid)
    return errors


def check_ranks(rows: list[dict]) -> list[str]:
    errors = []
    seen = set()
    for r in rows:
        try:
            rank = int(r["rank"])
        except ValueError:
            errors.append(f"Non-integer rank: {r['rank']!r}")
            continue
        if not 1 <= rank <= 100:
            errors.append(f"Rank {rank} outside [1, 100]")
        if rank in seen:
            errors.append(f"Duplicate rank: {rank}")
        seen.add(rank)
    missing = set(range(1, 101)) - seen
    if missing:
        errors.append(f"Missing ranks: {sorted(missing)}")
    return errors


def check_scores(rows: list[dict]) -> list[str]:
    errors = []
    sorted_rows = sorted(rows, key=lambda r: int(r["rank"]))
    try:
        scores = [float(r["score"]) for r in sorted_rows]
    except ValueError as e:
        return [f"Non-float score: {e}"]

    for i in range(len(scores) - 1):
        if scores[i] < scores[i + 1]:
            errors.append(
                f"Score not non-increasing at ranks {i+1},{i+2}: "
                f"{scores[i]:.4f} < {scores[i+1]:.4f}"
            )

    score_range = max(scores) - min(scores)
    if score_range < 1.0:
        errors.append(
            f"WARNING: Score range is very small ({score_range:.4f}) — "
            "distribution may be flat. Check pipeline weights."
        )
    return errors


def check_reasoning(rows: list[dict]) -> list[str]:
    errors = []
    for r in rows:
        reasoning = r.get("reasoning", "").strip()
        if not reasoning:
            errors.append(f"Empty reasoning for rank {r['rank']} ({r['candidate_id']})")
        elif reasoning in {"Good candidate", "High match", "Strong candidate"}:
            errors.append(f"Generic placeholder reasoning for rank {r['rank']}")
    return errors


def spot_check_top10(rows: list[dict]) -> list[str]:
    """Heuristic checks on the top-10 — requires reasoning strings to have
    candidate data and flags obviously wrong results."""
    warnings = []
    sorted_rows = sorted(rows, key=lambda r: int(r["rank"]))[:10]
    for r in sorted_rows:
        reasoning = r.get("reasoning", "")
        # Flag if reasoning mentions an obviously non-technical role
        for t in NON_TECHNICAL_TITLES:
            if t in reasoning.lower():
                warnings.append(
                    f"WARN rank {r['rank']}: reasoning mentions non-technical title "
                    f"({t!r}): {reasoning[:80]}"
                )
    return warnings


def main() -> int:
    path = sys.argv[1] if len(sys.argv) > 1 else "submission.csv"
    if not Path(path).exists():
        print(f"ERROR: file not found: {path}", file=sys.stderr)
        return 1

    print(f"Spot-checking: {path}")
    try:
        rows = load_rows(path)
    except Exception as exc:
        print(f"ERROR reading CSV: {exc}", file=sys.stderr)
        return 1

    all_errors: list[str] = []
    all_errors.extend(check_structure(rows))
    all_errors.extend(check_ids(rows))
    all_errors.extend(check_ranks(rows))
    all_errors.extend(check_scores(rows))
    all_errors.extend(check_reasoning(rows))

    warnings = spot_check_top10(rows)
    for w in warnings:
        print(f"  {w}")

    if rows:
        sorted_rows = sorted(rows, key=lambda r: int(r["rank"]))
        scores = [float(r["score"]) for r in sorted_rows]
        print(f"\nTotal rows  : {len(rows)}")
        print(f"Score range : {scores[-1]:.4f} – {scores[0]:.4f}")
        print("\nTop 5:")
        for r in sorted_rows[:5]:
            print(f"  #{r['rank']:>3} {r['candidate_id']}  score={float(r['score']):.4f}  {r['reasoning'][:75]}")
        print("\nBottom 3:")
        for r in sorted_rows[-3:]:
            print(f"  #{r['rank']:>3} {r['candidate_id']}  score={float(r['score']):.4f}  {r['reasoning'][:75]}")

    hard_errors = [e for e in all_errors if not e.startswith("WARNING")]
    warnings_only = [e for e in all_errors if e.startswith("WARNING")]

    for w in warnings_only:
        print(f"\n  {w}")

    if hard_errors:
        print(f"\n✗ {len(hard_errors)} error(s):")
        for e in hard_errors:
            print(f"  - {e}")
        return 1

    print("\n✓ Spot-check passed — run validate_submission.py for the full official check.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
