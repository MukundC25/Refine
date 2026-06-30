#!/usr/bin/env python3
"""rank.py — CLI entrypoint for the Refine candidate ranking system.

Runs the 3-stage hybrid pipeline end-to-end:
  candidates.jsonl + JD  →  submission.csv

No network calls are required at runtime when pre-computed embeddings and a
cached parsed JD are present in ./precomputed/. The script falls back to
on-the-fly embedding (slower) when the .npy file is missing, and prints a
warning so judges can see what's happening.

Exit codes:
    0   success
    1   output CSV failed validation
    2   required input file missing (candidates, JD)
"""

from __future__ import annotations

import argparse
import csv
import logging
import re
import sys
import time
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.app.core.jd_parser import ParsedJD
    from backend.app.core.ranking_engine import RankedCandidate, RankingEngine


PROGRESS_PREFIX = "[rank.py]"
CSV_HEADER = ["candidate_id", "rank", "score", "reasoning"]
CANDIDATE_ID_PATTERN = re.compile(r"^CAND_[0-9]{7}$")

EXIT_OK = 0
EXIT_VALIDATION_FAILED = 1
EXIT_MISSING_INPUT = 2


class MissingInputError(Exception):
    """Raised when a required input file cannot be found."""


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="rank.py",
        description="Rank candidates against a job description and write submission.csv.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--candidates", required=True, metavar="FILE",
                   help="Path to candidates .jsonl or .jsonl.gz file.")
    p.add_argument("--jd", default="./job_description.docx", metavar="FILE",
                   help="Path to JD file (.docx, .pdf, or .txt). Falls back to "
                        ".pdf with the same stem when the default .docx is missing.")
    p.add_argument("--embeddings", default="./precomputed/embeddings.npy", metavar="FILE",
                   help="Pre-computed candidate embeddings .npy file. When missing, "
                        "the script falls back to on-the-fly embedding (slower).")
    p.add_argument("--ids", default=None, metavar="FILE",
                   help="Companion candidate_ids.json. Defaults to "
                        "<embeddings-stem>_ids.json alongside --embeddings.")
    p.add_argument("--parsed-jd-cache", default="./precomputed/parsed_jd.json", metavar="FILE",
                   help="Cache file for the parsed JD. If present, the Gemini "
                        "call is skipped — needed for no-network runs.")
    p.add_argument("--rich-reasoning", default="./precomputed/rich_reasoning.json", metavar="FILE",
                   help="Optional pre-computed rich-reasoning cache.")
    p.add_argument("--out", required=True, metavar="FILE",
                   help="Output CSV path.")
    p.add_argument("--top-n", type=int, default=100, metavar="N",
                   help="Number of candidates in final output (default: 100).")
    p.add_argument("--stage1-n", type=int, default=5000, metavar="N",
                   help="Stage 1 shortlist size (default: 5000).")
    p.add_argument("--stage2-n", type=int, default=200, metavar="N",
                   help="Stage 2 shortlist size (default: 200).")
    p.add_argument("--log-level", default="INFO",
                   choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                   help="Logging level (default: INFO).")
    p.add_argument("--strict-validation", action="store_true",
                   help="Enforce the official 100-row submission rule even when "
                        "--top-n differs from 100. Off by default for test runs.")
    return p


def configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level),
        format="%(asctime)s  %(levelname)-7s  %(message)s",
        datefmt="%H:%M:%S",
    )


def progress(msg: str) -> None:
    """Emit a [rank.py] progress line to stdout and flush so judges see it live."""
    print(f"{PROGRESS_PREFIX} {msg}", flush=True)


def resolve_jd_path(jd_arg: str) -> Path | None:
    """Return the JD file path if it exists, trying .pdf sibling when .docx is missing."""
    p = Path(jd_arg)
    if p.exists():
        return p
    if p.suffix.lower() == ".docx":
        pdf = p.with_suffix(".pdf")
        if pdf.exists():
            return pdf
    return None


def validate_input_files(args: argparse.Namespace) -> Path:
    """Check required inputs and return the resolved JD path. Raises MissingInputError."""
    if not Path(args.candidates).exists():
        raise MissingInputError(f"candidates file not found: {args.candidates}")
    jd_path = resolve_jd_path(args.jd)
    if jd_path is None:
        raise MissingInputError(
            f"JD file not found: {args.jd} (also tried .pdf fallback)"
        )
    return jd_path


def load_jd(jd_path: Path, cache_path: str) -> "ParsedJD":
    """Parse or load a cached JD. Hits Gemini only when no cache exists."""
    from backend.app.core.jd_parser import get_or_parse_jd
    try:
        return get_or_parse_jd(str(jd_path), cache_path=cache_path)
    except Exception as exc:
        raise MissingInputError(
            f"failed to parse JD: {exc}\n"
            f"Hint: pre-compute the JD cache offline (set GEMINI_API_KEY and run "
            f"once) so this run can use {cache_path} without network access."
        ) from exc


def build_engine(args: argparse.Namespace) -> "RankingEngine":
    """Construct a RankingEngine. Embeddings are optional — falls back to on-the-fly."""
    from backend.app.core.ranking_engine import RankingEngine

    rich_path = args.rich_reasoning if Path(args.rich_reasoning).exists() else None
    if rich_path:
        progress(f"Rich-reasoning cache: {rich_path}")

    if not Path(args.embeddings).exists():
        progress(
            f"WARNING: embeddings not found at {args.embeddings} — "
            "falling back to on-the-fly embedding (slower)."
        )
        return RankingEngine(rich_reasoning_path=rich_path)

    return RankingEngine(
        embeddings_path=str(args.embeddings),
        ids_path=args.ids,
        rich_reasoning_path=rich_path,
    )


def _missing_ml_dep_message(args: argparse.Namespace, exc: ModuleNotFoundError) -> str:
    return (
        f"required ML library not installed: {exc.name}.\n"
        f"Hint: pre-compute embeddings offline (so this run does not need the "
        f"model) by installing sentence-transformers and running:\n"
        f"    python precompute_embeddings.py --candidates {args.candidates} "
        f"--out {args.embeddings}"
    )


def write_submission_csv(ranked: list["RankedCandidate"], output_path: str) -> None:
    """Write the final CSV with columns: candidate_id, rank, score, reasoning.

    Assumes `ranked` is already sorted by rank ascending — which RankingEngine
    guarantees. csv.writer handles quoting of commas/quotes inside reasoning.
    """
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(CSV_HEADER)
        for rc in ranked:
            w.writerow([
                rc.candidate.candidate_id,
                rc.rank,
                round(rc.final_score, 4),
                rc.reasoning,
            ])


def validate_output_csv(
    output_path: str,
    expected_rows: int,
    strict: bool = False,
) -> list[str]:
    """Inline mirror of validate_submission.py's checks (no external dependency).

    When *strict* is True, also enforce the official rule of exactly 100 rows.
    Otherwise validate against *expected_rows* (useful for partial runs).
    """
    errors: list[str] = []
    p = Path(output_path)
    if p.suffix.lower() != ".csv":
        errors.append("Output file must have .csv extension.")

    try:
        with p.open("r", encoding="utf-8", newline="") as fh:
            reader = csv.reader(fh)
            try:
                header = next(reader)
            except StopIteration:
                errors.append("CSV is empty (no header row).")
                return errors
            if header != CSV_HEADER:
                errors.append(
                    f"Header must be {','.join(CSV_HEADER)}; got {','.join(header)}."
                )
            rows = [r for r in reader if any(c.strip() for c in r)]
    except UnicodeDecodeError:
        errors.append("File must be UTF-8 encoded.")
        return errors
    except OSError as exc:
        errors.append(f"Cannot read file: {exc}")
        return errors

    target_rows = 100 if strict else expected_rows
    if len(rows) != target_rows:
        errors.append(f"Expected exactly {target_rows} data rows; got {len(rows)}.")

    seen_ids: set[str] = set()
    seen_ranks: set[int] = set()
    parsed: list[tuple[int, float, str]] = []
    for i, row in enumerate(rows, start=2):
        if len(row) != 4:
            errors.append(f"Row {i}: expected 4 columns, got {len(row)}.")
            continue
        cid, rank_s, score_s, _reasoning = row
        cid = cid.strip()
        if not CANDIDATE_ID_PATTERN.match(cid):
            errors.append(f"Row {i}: invalid candidate_id {cid!r}.")
        elif cid in seen_ids:
            errors.append(f"Row {i}: duplicate candidate_id {cid!r}.")
        else:
            seen_ids.add(cid)
        try:
            rank = int(rank_s)
            if rank in seen_ranks:
                errors.append(f"Row {i}: duplicate rank {rank}.")
            else:
                seen_ranks.add(rank)
        except ValueError:
            errors.append(f"Row {i}: rank must be integer, got {rank_s!r}.")
            continue
        try:
            score = float(score_s)
        except ValueError:
            errors.append(f"Row {i}: score must be float, got {score_s!r}.")
            continue
        parsed.append((rank, score, cid))

    parsed.sort(key=lambda x: x[0])
    for i in range(len(parsed) - 1):
        r1, s1, c1 = parsed[i]
        r2, s2, c2 = parsed[i + 1]
        if s1 < s2:
            errors.append(
                f"Score must be non-increasing by rank: rank {r1} ({s1}) < rank {r2} ({s2})."
            )
        if s1 == s2 and c1 > c2:
            errors.append(
                f"Tie-break: equal scores at ranks {r1},{r2} require "
                f"candidate_id ascending ({c1!r} > {c2!r})."
            )

    return errors


def run(args: argparse.Namespace) -> int:
    """Drive the pipeline. Returns an exit code."""
    configure_logging(args.log_level)
    start = time.perf_counter()

    try:
        jd_path = validate_input_files(args)
    except MissingInputError as exc:
        progress(f"ERROR: {exc}")
        return EXIT_MISSING_INPUT

    progress(f"Parsing job description: {jd_path}")
    try:
        jd = load_jd(jd_path, args.parsed_jd_cache)
    except MissingInputError as exc:
        progress(f"ERROR: {exc}")
        return EXIT_MISSING_INPUT
    progress(
        f"JD parsed: {jd.role_title or '(no title)'} | "
        f"required_skills: {', '.join(jd.required_skills[:5])}"
    )

    progress(f"Building ranking engine (embeddings: {args.embeddings})...")
    engine = build_engine(args)

    progress(
        f"Running pipeline: stage1_n={args.stage1_n}, stage2_n={args.stage2_n}, "
        f"top_n={args.top_n}"
    )
    t_pipeline = time.perf_counter()
    try:
        ranked = engine.run(
            candidates_path=args.candidates,
            jd=jd,
            top_n_stage1=args.stage1_n,
            top_n_stage2=args.stage2_n,
            top_n_final=args.top_n,
        )
    except ModuleNotFoundError as exc:
        progress(f"ERROR: {_missing_ml_dep_message(args, exc)}")
        return EXIT_MISSING_INPUT
    pipeline_elapsed = time.perf_counter() - t_pipeline
    progress(f"Pipeline complete: {len(ranked)} candidates ranked [{pipeline_elapsed:.1f}s]")

    progress(f"Writing submission CSV: {args.out}")
    write_submission_csv(ranked, args.out)

    progress("Validating output CSV...")
    errors = validate_output_csv(args.out, expected_rows=len(ranked),
                                 strict=args.strict_validation)
    if errors:
        progress("✗ Validation FAILED:")
        for err in errors:
            progress(f"  - {err}")
        return EXIT_VALIDATION_FAILED

    progress(
        f"✓ Validation passed ({len(ranked)} rows, ranks 1–{len(ranked)}, "
        f"scores non-increasing)"
    )
    progress(f"✓ Done in {time.perf_counter() - start:.1f}s → {args.out}")
    return EXIT_OK


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return run(args)


if __name__ == "__main__":
    sys.exit(main())
