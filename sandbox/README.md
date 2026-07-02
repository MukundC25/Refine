---
title: Redrob AI Candidate Ranker
emoji: 🎯
colorFrom: purple
colorTo: indigo
sdk: streamlit
sdk_version: 1.35.0
app_file: app.py
pinned: false
license: mit
---

# Redrob AI — Intelligent Candidate Ranking System

A 3-stage hybrid AI pipeline that ranks candidates against a job description
the way a great recruiter would — not by keyword matching, but by understanding
career signals, skill credibility, and behavioral fit.

**Challenge:** India Runs Data & AI Challenge — Redrob AI Track

## How to run locally

```bash
cd sandbox
pip install -r requirements.txt
streamlit run app.py
```

## Pipeline

```
Stage 1: Rule-Based Pre-Screen (YoE, title, skills overlap, company type)
Stage 2: Semantic Re-Rank (sentence-transformer embeddings + skills trust + career trajectory)
Stage 3: Behavioral Signal Boost (Redrob platform signals — response rate, GitHub, interview completion)
```
