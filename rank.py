#!/usr/bin/env python3
"""
rank.py — CLI entrypoint for the Refine candidate ranking system.

Usage
-----
    python rank.py --jd <job_description.txt> --candidates <candidates.jsonl> [--top-k 100]

Arguments
---------
    --jd            Path to a plain-text file containing the job description.
    --candidates    Path to a JSONL file where each line is one candidate profile.
    --top-k         Number of top-ranked candidates to include in submission.csv
                    (default: 100).
    --output        Path for the output CSV (default: submission.csv).

Output
------
    A CSV file at --output with columns:
        candidate_id, rank, score, shortlisted

Full implementation: Issue 012
"""

from __future__ import annotations

import argparse
import sys


USAGE = __doc__


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="rank.py",
        description="Rank candidates against a job description.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=USAGE,
    )
    parser.add_argument("--jd", metavar="FILE", help="Path to job description text file.")
    parser.add_argument("--candidates", metavar="FILE", help="Path to candidates JSONL file.")
    parser.add_argument("--top-k", type=int, default=100, metavar="N", help="Top-K candidates to emit (default: 100).")
    parser.add_argument("--output", default="submission.csv", metavar="FILE", help="Output CSV path (default: submission.csv).")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    # If called with no required arguments, print usage and exit cleanly.
    if args.jd is None or args.candidates is None:
        parser.print_help()
        print("\n⚠  rank.py: --jd and --candidates are required.\n", file=sys.stderr)
        return 2

    # ------------------------------------------------------------------ #
    #  Full implementation wired in Issue 012.                            #
    # ------------------------------------------------------------------ #
    print(f"[rank.py] JD file      : {args.jd}")
    print(f"[rank.py] Candidates   : {args.candidates}")
    print(f"[rank.py] Top-K        : {args.top_k}")
    print(f"[rank.py] Output       : {args.output}")
    print("[rank.py] Ranking engine not yet implemented — see Issue 012.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
