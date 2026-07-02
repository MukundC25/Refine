# Submission Checklist — Redrob AI Challenge

Run these checks in order before uploading to the challenge portal.

---

## A. Environment

```bash
# Python version must be 3.11.x
python --version

# Install deps in a clean venv
python -m venv .venv_submit && source .venv_submit/bin/activate
pip install -r backend/requirements.txt

# Confirm model is cached (avoids network call during ranking)
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2'); print('model OK')"
```

---

## B. Pre-Computation

```bash
# Generate candidate embeddings (~3 min)
python precompute_embeddings.py \
  --candidates ./candidates.jsonl \
  --out ./precomputed/embeddings.npy

# Verify artefacts
python scripts/verify_precomputed.py --precomputed ./precomputed
# Expected: ✓ All precomputed artefacts verified
```

---

## C. Full Pipeline Run

```bash
time python rank.py \
  --candidates ./candidates.jsonl \
  --jd ./job_description.docx \
  --embeddings ./precomputed/embeddings.npy \
  --ids ./precomputed/candidate_ids.json \
  --out ./submission.csv \
  --log-level INFO
```

Expected:
- Exit code 0
- Runtime ≤ 5 minutes (with pre-computed embeddings)
- `[rank.py] ✓ Done` line printed at the end

---

## D. Validate Output

```bash
# Official validator
python validate_submission.py ./submission.csv
# Expected: "Submission is valid."

# Spot-check (sanity review of top results)
python scripts/spot_check.py ./submission.csv
# Expected: ✓ Spot-check passed
```

---

## E. Manual Spot-Check

Review top-10 results:
- [ ] Rank 1 candidate has ≥ 5 years experience in a relevant domain
- [ ] No Marketing Manager / HR / Accountant-only profiles in top 20
- [ ] Rank 1 score is meaningfully higher than rank 100 score (spread ≥ 5 pts)
- [ ] Reasoning strings reference actual candidate data (YoE, company, skills)
- [ ] No known honeypot-adjacent profiles (CAND_0000002 pattern) in top 100

---

## F. Metadata & Repo

- [ ] `submission_metadata.yaml` — fill in `primary_contact.email` and `phone`
- [ ] `submission_metadata.yaml` — update `sandbox_link` with live HF Spaces URL
- [ ] `git status` shows clean working tree (all changes committed)
- [ ] `.gitignore` excludes `submission.csv`, `candidates.jsonl`, `*.npy`

```bash
# Verify YAML is valid
python -c "import yaml; yaml.safe_load(open('submission_metadata.yaml')); print('YAML OK')"
```

---

## G. Docker Check

```bash
docker build -f Dockerfile.rank -t redrob-ranker .
docker run --rm redrob-ranker --help
# Expected: prints rank.py usage, exit 0
```

---

## H. Submit

1. Open the challenge portal
2. Upload `submission.csv`
3. Fill in metadata: team name, sandbox link, GitHub repo, reproduce command
4. Confirm `uses_gpu_for_inference: false` and `has_network_during_ranking: false`
5. Submit and note the timestamp

---

## I. Post-Submission

```bash
# Tag the commit
git tag submission-v1 && git push origin submission-v1

# Archive locally
cp submission.csv "submission_v1_$(date +%Y%m%d).csv"
```

---

## Scoring Reference

| Metric   | Weight | What it rewards              |
|----------|--------|------------------------------|
| NDCG@10  | 50 %   | Top-10 order exactly right   |
| NDCG@50  | 30 %   | Top-50 quality               |
| MAP      | 15 %   | All-relevance precision      |
| P@10     |  5 %   | How many top-10 are relevant |

Top-10 order dominates. Only resubmit if there is a clear algorithmic bug,
not for minor weight tuning.
