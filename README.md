# Refine × Redrob — Intelligent Candidate Ranking System

> A 3-stage hybrid AI pipeline that ranks 100,000 candidates against a job
> description the way a great recruiter would — not by keyword matching, but
> by understanding career signals, skill credibility, and behavioural fit.

**Submission for:** India Runs Data & AI Challenge — Redrob AI Track  
**Sandbox demo:** [Live on HuggingFace Spaces](https://huggingface.co/spaces/MukundC25/redrob-ranker)

---

## Quick Start

### 1. Install dependencies
```bash
pip install -r backend/requirements.txt
```

### 2. Pre-compute embeddings (one-time, ~3 minutes)
```bash
python precompute_embeddings.py \
  --candidates ./candidates.jsonl \
  --out ./precomputed/embeddings.npy
```

### 3. Run ranking
```bash
python rank.py \
  --candidates ./candidates.jsonl \
  --jd ./job_description.docx \
  --out ./submission.csv
```

### 4. Validate output
```bash
python validate_submission.py ./submission.csv
```

### 5. Run with Docker (fully reproducible)
```bash
# Build the CLI image (model baked in — works offline)
docker build -f Dockerfile.rank -t redrob-ranker .

docker run --rm \
  -v $(pwd)/data:/data \
  -v $(pwd)/precomputed:/app/precomputed \
  redrob-ranker \
    --candidates /data/candidates.jsonl \
    --jd /data/job_description.docx \
    --out /data/submission.csv
```

---

## Architecture

```
candidates.jsonl (100K)
       │
  Stage 1: Rule Pre-Screen
  ├── Honeypot detection (issue 004)
  └── Rule scorer — YoE, title, skills overlap, company type (issue 006)
       │  Top ~5,000 candidates
  Stage 2: Semantic Re-Rank
  ├── all-MiniLM-L6-v2 embeddings, offline (issue 005)
  ├── Trust-weighted skills match (issue 007)
  └── Career trajectory analysis (issue 008)
       │  Top ~200 candidates
  Stage 3: Behavioral Signal Boost
  └── Redrob platform signals (issue 009)
       │  Top 100 candidates
  submission.csv → candidate_id, rank, score, reasoning
```

---

## Key Design Decisions

**Why local embeddings instead of Gemini during ranking?**  
The challenge spec requires `has_network_during_ranking: false`. Gemini is used
only once at setup time to parse the JD; the result is cached in
`precomputed/parsed_jd.json`. All inference uses `all-MiniLM-L6-v2` running
locally on CPU.

**Why behavioural signals matter**  
The `redrob_signals` block in the candidate schema is the highest-differentiation
signal in the dataset. Keyword matchers ignore it entirely. This system uses
recruiter response rate, interview completion rate, GitHub activity, and offer
acceptance to separate candidates who convert from those who ghost.

**Why trust-weighted skills over raw keyword overlap**  
A candidate who self-declares "expert" in 15 AI skills with 0 endorsements and
0 duration months is a keyword stuffer. The skill trust formula:
- Platform assessment score overrides self-declared proficiency (60/40 blend)
- Endorsement count adds log-scale credibility boost
- Usage duration saturates at 36 months — beyond that, extra duration adds nothing

**Honeypot strategy**  
Candidates are flagged if they show: YoE inconsistent with career span,
bulk unendorsed expert skills, non-technical career with many specific AI skill
claims, or perfect platform engagement scores (all 1.0 is statistically
implausible). Flagged candidates receive a penalty multiplier (0.7 or 0.4);
three or more flags → disqualified (multiplier 0.0).

---

## Repo Structure

```
Refine/
├── rank.py                        CLI entrypoint (issue 012)
├── precompute_embeddings.py       Offline embedding pre-computation
├── Dockerfile.rank                Standalone CLI Docker image (issue 022)
├── docker-compose.yml             Web stack orchestration (issue 022)
├── submission_metadata.yaml       Challenge submission metadata (issue 023)
├── validate_submission.py         Official challenge validator
│
├── backend/
│   ├── app/
│   │   ├── core/
│   │   │   ├── candidate_loader.py     (issue 003)
│   │   │   ├── honeypot_detector.py    (issue 004)
│   │   │   ├── embedding_service.py    (issue 005)
│   │   │   ├── rule_scorer.py          (issue 006)
│   │   │   ├── skill_matcher.py        (issue 007)
│   │   │   ├── career_analyzer.py      (issue 008)
│   │   │   ├── signal_scorer.py        (issue 009)
│   │   │   ├── ranking_engine.py       (issue 010)
│   │   │   ├── reasoning_generator.py  (issue 011)
│   │   │   └── jd_parser.py            (issue 002)
│   │   ├── routers/
│   │   │   ├── ranking.py              (issue 013)
│   │   │   └── auth.py
│   │   └── main.py
│   └── tests/                     pytest test suite (all issues)
│
├── frontend/                      React + TypeScript recruiter dashboard
│   └── src/components/recruiter/  (issues 017–020)
│
└── sandbox/                       Streamlit demo for HuggingFace Spaces (issue 021)
    ├── app.py
    ├── sample_candidates.json
    └── requirements.txt
```

---

## Running the Web App

```bash
# Start the full stack (backend + frontend)
docker-compose up

# Backend API: http://localhost:8000
# Frontend dashboard: http://localhost:5173
```

Or without Docker:
```bash
# Backend
cd backend
PYTHONPATH=..:. uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend
npm install && npm run dev
```

---

## Running Tests

```bash
pytest backend/tests/ -v
```

The test suite covers all 12 backend modules. Tests that require
`sentence-transformers` or a live `GEMINI_API_KEY` are handled gracefully:
the embedding service tests skip if the model is not installed; the JD parser
integration test skips if no API key is set.

---

## Submission Checklist

- [ ] `precomputed/embeddings.npy` generated from `candidates.jsonl`
- [ ] `precomputed/parsed_jd.json` generated from `job_description.docx`
- [ ] `python rank.py ... --out submission.csv` exits 0
- [ ] `python validate_submission.py submission.csv` prints "Submission is valid."
- [ ] Scores non-increasing, all ranks 1–100 unique, no duplicate candidate IDs
- [ ] `submission_metadata.yaml` has no `YOUR_USERNAME` or empty contact fields
- [ ] Sandbox link is live and accessible without login
- [ ] Git commit tagged before portal upload
