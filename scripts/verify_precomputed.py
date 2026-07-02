#!/usr/bin/env python3
"""verify_precomputed.py — Check that precomputed/ artefacts are ready for ranking.

Verifies:
  - embeddings.npy   exists, float32, shape (N, 384), no NaNs
  - candidate_ids.json  exists, exactly N entries, all CAND_XXXXXXX format
  - N matches between both files
  - parsed_jd.json  exists and is valid JSON

Usage:
    python scripts/verify_precomputed.py [--precomputed ./precomputed]

Exits 0 when all checks pass.
"""

import argparse
import json
import re
import sys
from pathlib import Path

import numpy as np

CANDIDATE_ID_RE = re.compile(r"^CAND_[0-9]{7}$")
EXPECTED_DIM = 384


def verify_embeddings(npy_path: Path) -> tuple[int, list[str]]:
    errors = []
    if not npy_path.exists():
        return 0, [f"embeddings file not found: {npy_path}"]

    matrix = np.load(str(npy_path))
    n_rows, n_cols = matrix.shape

    if matrix.dtype != np.float32:
        errors.append(f"embeddings dtype is {matrix.dtype}, expected float32")
    if n_cols != EXPECTED_DIM:
        errors.append(f"embedding dimension is {n_cols}, expected {EXPECTED_DIM}")
    if np.isnan(matrix).any():
        nan_count = int(np.isnan(matrix).sum())
        errors.append(f"embeddings contain {nan_count} NaN values")

    size_mb = npy_path.stat().st_size / 1024 / 1024
    print(f"  embeddings.npy : shape={matrix.shape}, dtype={matrix.dtype}, size={size_mb:.1f} MB")
    return n_rows, errors


def verify_ids(ids_path: Path, expected_n: int) -> list[str]:
    errors = []
    if not ids_path.exists():
        return [f"ids file not found: {ids_path}"]

    ids = json.loads(ids_path.read_text(encoding="utf-8"))
    if not isinstance(ids, list):
        return ["candidate_ids.json must be a JSON array"]

    print(f"  candidate_ids.json : {len(ids)} entries")

    if expected_n > 0 and len(ids) != expected_n:
        errors.append(f"ids count {len(ids)} != embeddings rows {expected_n}")

    bad_ids = [cid for cid in ids if not CANDIDATE_ID_RE.match(str(cid))]
    if bad_ids:
        errors.append(
            f"{len(bad_ids)} invalid candidate_id(s): {bad_ids[:5]}{'…' if len(bad_ids) > 5 else ''}"
        )

    if len(set(ids)) != len(ids):
        errors.append("candidate_ids.json contains duplicate IDs")

    return errors


def verify_parsed_jd(jd_path: Path) -> list[str]:
    if not jd_path.exists():
        return [f"parsed_jd.json not found: {jd_path} — run precompute step first"]
    try:
        d = json.loads(jd_path.read_text(encoding="utf-8"))
        role = d.get("role_title", "(no title)")
        skills = d.get("required_skills", [])
        print(f"  parsed_jd.json : role={role!r}, required_skills={skills[:4]}")
        return []
    except json.JSONDecodeError as e:
        return [f"parsed_jd.json is not valid JSON: {e}"]


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify precomputed artefacts.")
    parser.add_argument("--precomputed", default="./precomputed", metavar="DIR")
    args = parser.parse_args()

    precomputed = Path(args.precomputed)
    print(f"Checking {precomputed.resolve()}/")

    all_errors: list[str] = []

    n_rows, emb_errors = verify_embeddings(precomputed / "embeddings.npy")
    all_errors.extend(emb_errors)

    id_errors = verify_ids(precomputed / "candidate_ids.json", n_rows)
    all_errors.extend(id_errors)

    jd_errors = verify_parsed_jd(precomputed / "parsed_jd.json")
    all_errors.extend(jd_errors)

    if all_errors:
        print(f"\n✗ {len(all_errors)} error(s):")
        for e in all_errors:
            print(f"  - {e}")
        return 1

    print("\n✓ All precomputed artefacts verified — ready to run rank.py.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
