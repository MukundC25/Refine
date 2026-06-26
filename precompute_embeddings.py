#!/usr/bin/env python3
"""
precompute_embeddings.py — Offline pre-computation of candidate embeddings.

Streams a candidates JSONL file, builds a rich text representation for each
candidate using build_candidate_text(), embeds in batches with a local
sentence-transformers model, and saves the result as a float32 NumPy matrix
plus a parallel candidate_ids.json index.

Must be run from the repository root so that the ``backend`` package is on
the Python path:

    cd /path/to/Refine
    python precompute_embeddings.py \\
      --candidates ./candidates.jsonl \\
      --out ./precomputed/embeddings.npy \\
      --ids ./precomputed/candidate_ids.json \\
      --batch-size 512 \\
      --model all-MiniLM-L6-v2

Output files
------------
    <--out>   float32 NumPy matrix, shape (N, 384)  — ~153 MB for 100 K rows
    <--ids>   JSON array of N candidate_id strings, row-aligned with the matrix

Runtime estimate
----------------
    100 K candidates, all-MiniLM-L6-v2, batch-size 512, CPU-only: ~90 seconds
    (load .npy at ranking time: ~0.5 s; embed JD: ~0.01 s; cosine 100 K: ~0.3 s)
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="precompute_embeddings.py",
        description=(
            "Pre-compute sentence-transformer embeddings for all candidates "
            "and save to a .npy matrix + candidate_ids.json index."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument(
        "--candidates",
        required=True,
        metavar="FILE",
        help="Path to candidates .jsonl or .jsonl.gz file.",
    )
    p.add_argument(
        "--out",
        required=True,
        metavar="FILE",
        help="Destination .npy path for the embedding matrix.",
    )
    p.add_argument(
        "--ids",
        default=None,
        metavar="FILE",
        help=(
            "Path for the companion candidate_ids.json "
            "(default: <out-stem>_ids.json alongside --out)."
        ),
    )
    p.add_argument(
        "--batch-size",
        type=int,
        default=512,
        metavar="N",
        help="Candidates per embedding batch (default: 512).",
    )
    p.add_argument(
        "--model",
        default="all-MiniLM-L6-v2",
        metavar="MODEL",
        help="sentence-transformers model name (default: all-MiniLM-L6-v2).",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    candidates_path = args.candidates
    out_path = args.out
    ids_path = args.ids
    batch_size = args.batch_size
    model_name = args.model

    if not Path(candidates_path).exists():
        logger.error("Candidates file not found: %s", candidates_path)
        return 1

    logger.info("Candidates  : %s", candidates_path)
    logger.info("Output .npy : %s", out_path)
    if ids_path:
        logger.info("IDs file    : %s", ids_path)
    logger.info("Batch size  : %d", batch_size)
    logger.info("Model       : %s", model_name)
    logger.info("")

    from backend.app.core.embedding_service import precompute_candidate_embeddings

    t0 = time.perf_counter()
    precompute_candidate_embeddings(
        candidates_path=candidates_path,
        output_path=out_path,
        batch_size=batch_size,
        ids_path=ids_path,
        model_name=model_name,
        show_progress=True,
    )
    elapsed = time.perf_counter() - t0

    logger.info("")
    logger.info("Done in %.1f seconds.", elapsed)
    return 0


if __name__ == "__main__":
    sys.exit(main())
