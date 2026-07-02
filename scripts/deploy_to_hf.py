#!/usr/bin/env python3
"""Deploy the sandbox to HuggingFace Spaces.

Usage:
    python scripts/deploy_to_hf.py --token YOUR_HF_WRITE_TOKEN

Get a write token at: https://huggingface.co/settings/tokens
"""

import argparse
import sys
from pathlib import Path

REPO_ID = "Mukund25/redrob-ranker"
SPACE_ROOT = Path(__file__).resolve().parent.parent / "sandbox"
BACKEND_SRC = Path(__file__).resolve().parent.parent / "backend"

FILES_TO_UPLOAD = [
    "app.py",
    "requirements.txt",
    "README.md",
    "sample_candidates.json",
    "job_description.txt",
    # Backend package bundled for HF Spaces
    "backend/__init__.py",
    "backend/app/__init__.py",
    "backend/app/core/__init__.py",
    "backend/app/core/candidate_loader.py",
    "backend/app/core/career_analyzer.py",
    "backend/app/core/embedding_service.py",
    "backend/app/core/honeypot_detector.py",
    "backend/app/core/jd_parser.py",
    "backend/app/core/logging_config.py",
    "backend/app/core/ranking_engine.py",
    "backend/app/core/reasoning_generator.py",
    "backend/app/core/rule_scorer.py",
    "backend/app/core/signal_scorer.py",
    "backend/app/core/skill_matcher.py",
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--token", required=True, help="HuggingFace write token")
    args = parser.parse_args()

    try:
        from huggingface_hub import HfApi
    except ImportError:
        print("Run: pip install huggingface_hub")
        sys.exit(1)

    api = HfApi(token=args.token)

    print(f"Uploading {len(FILES_TO_UPLOAD)} files to {REPO_ID}...")

    for relative_path in FILES_TO_UPLOAD:
        local_path = SPACE_ROOT / relative_path
        if not local_path.exists():
            print(f"  SKIP (not found): {relative_path}")
            continue
        api.upload_file(
            path_or_fileobj=str(local_path),
            path_in_repo=relative_path,
            repo_id=REPO_ID,
            repo_type="space",
        )
        print(f"  ✓ {relative_path}")

    print(f"\nDone! View your Space at: https://huggingface.co/spaces/{REPO_ID}")


if __name__ == "__main__":
    main()
