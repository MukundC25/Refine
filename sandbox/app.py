import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

# On HuggingFace Spaces, app.py and backend/ sit side-by-side at the Space root.
# Locally, app.py is in sandbox/ and backend/ is one level up.
_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))               # Space root OR sandbox/
sys.path.insert(0, str(_HERE / "backend"))   # bundled backend copy

from app.core.candidate_loader import CandidateRecord, validate_candidate, build_candidate_text
from app.core.career_analyzer import analyze_career
from app.core.embedding_service import EmbeddingService
from app.core.honeypot_detector import detect_honeypot
from app.core.jd_parser import ParsedJD
from app.core.ranking_engine import compute_final_score
from app.core.reasoning_generator import generate_reasoning
from app.core.rule_scorer import (
    _DEFAULT_PREFERRED_SKILLS,
    _DEFAULT_REQUIRED_SKILLS,
    score_candidate,
)
from app.core.signal_scorer import compute_behavioral_score
from app.core.skill_matcher import combined_skills_score

st.set_page_config(
    page_title="Redrob AI Ranker Demo",
    page_icon="🎯",
    layout="wide",
)

SAMPLE_CANDIDATES_PATH = Path(__file__).parent / "sample_candidates.json"
SAMPLE_JD_PATH = Path(__file__).parent / "job_description.txt"


@st.cache_resource
def get_embedding_service() -> EmbeddingService:
    return EmbeddingService()


def load_sample_jd() -> str:
    if SAMPLE_JD_PATH.exists():
        return SAMPLE_JD_PATH.read_text(encoding="utf-8")
    return "Senior AI Engineer with 5-9 years experience in embeddings, NLP, Python."


def build_parsed_jd(text: str) -> ParsedJD:
    """Build a ParsedJD from raw text without calling Gemini (no network needed)."""
    import re
    text_lower = text.lower()
    yoe_min, yoe_max = 5.0, 9.0
    if m := re.search(r"(\d+)\s*[-–to]+\s*(\d+)\s*years?", text_lower):
        yoe_min, yoe_max = float(m.group(1)), float(m.group(2))
    elif m := re.search(r"(\d+)\+?\s*years?", text_lower):
        yoe_min = float(m.group(1))
        yoe_max = yoe_min + 4

    return ParsedJD(
        raw_text=text,
        role_title="Senior AI Engineer",
        required_skills=_DEFAULT_REQUIRED_SKILLS,
        preferred_skills=_DEFAULT_PREFERRED_SKILLS,
        disqualifying_signals=[],
        min_years_experience=yoe_min,
        max_years_experience=yoe_max,
        preferred_locations=[],
        notice_period_preference_days=30,
        seniority_level="senior",
        industry_preference="product_company",
        work_mode="hybrid",
        role_embedding_text=text,
        jd_hash="sandbox_demo",
        vibe_signals=[],
        hiring_context="",
    )


def load_candidates() -> list[CandidateRecord]:
    raw = json.loads(SAMPLE_CANDIDATES_PATH.read_text(encoding="utf-8"))
    return [r for r in (validate_candidate(d) for d in raw) if r is not None]


def run_ranking(jd_text: str, weights: dict):
    jd = build_parsed_jd(jd_text)
    candidates = load_candidates()
    svc = get_embedding_service()
    jd_embedding = svc.embed_text(jd.role_embedding_text)

    progress = st.progress(0, text="Starting pipeline...")
    results = []
    total = len(candidates)

    for i, candidate in enumerate(candidates):
        honeypot = detect_honeypot(candidate)
        rule = score_candidate(candidate, jd)
        cand_text = build_candidate_text(candidate)
        cand_emb = svc.embed_text(cand_text)
        # Normalise and compute cosine
        jd_n = jd_embedding / (np.linalg.norm(jd_embedding) + 1e-9)
        c_n = cand_emb / (np.linalg.norm(cand_emb) + 1e-9)
        emb_sim = float(np.dot(jd_n, c_n))

        skills = combined_skills_score(candidate, jd, jd_embedding, svc)
        career = analyze_career(candidate, jd)
        behavioral = compute_behavioral_score(candidate)
        final = compute_final_score(rule, emb_sim, skills, career, behavioral, honeypot, weights)
        reasoning = generate_reasoning(
            candidate, rule, emb_sim, skills, career, behavioral, honeypot, final, jd=jd,
        )
        results.append({
            "candidate": candidate,
            "rule": rule,
            "emb_sim": emb_sim,
            "skills": skills,
            "career": career,
            "behavioral": behavioral,
            "honeypot": honeypot,
            "final_score": final,
            "reasoning": reasoning,
        })
        progress.progress((i + 1) / total, text=f"Processing candidate {i+1}/{total}...")

    results.sort(key=lambda x: (-x["final_score"], x["candidate"].candidate_id))
    for rank, r in enumerate(results, 1):
        r["rank"] = rank

    progress.empty()
    st.session_state["results"] = results
    st.session_state["jd"] = jd


def display_results():
    results = st.session_state.get("results")
    if not results:
        st.info("Run the ranking pipeline to see results here.")
        return

    tab1, tab2, tab3, tab4 = st.tabs(
        ["📋 Ranked Results", "🔍 Score Breakdown", "⚙️ Pipeline", "ℹ️ About"]
    )

    with tab1:
        st.subheader(f"Ranked {len(results)} Candidates")
        rows = []
        for r in results:
            c = r["candidate"]
            rows.append({
                "Rank": r["rank"],
                "ID": c.candidate_id,
                "Headline": c.profile.headline[:50],
                "Title": c.profile.current_title,
                "Company": c.profile.current_company,
                "YoE": c.profile.years_of_experience,
                "Score": round(r["final_score"], 2),
                "Flags": "⚠️" if r["honeypot"].flags else "✓",
                "Reasoning": r["reasoning"][:80] + "…",
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        candidate_ids = [r["candidate"].candidate_id for r in results]
        selected = st.selectbox("Select candidate for detailed breakdown →", candidate_ids)
        st.session_state["selected_id"] = selected

    with tab2:
        sel_id = st.session_state.get("selected_id")
        if not sel_id:
            st.info("Select a candidate in the Ranked Results tab.")
        else:
            sel = next((r for r in results if r["candidate"].candidate_id == sel_id), None)
            if sel is None:
                st.error("Candidate not found.")
            else:
                c = sel["candidate"]
                st.subheader(f"#{sel['rank']} — {c.profile.headline}")
                st.caption(
                    f"{c.profile.current_title} @ {c.profile.current_company} | "
                    f"{c.profile.years_of_experience:.1f} yrs"
                )

                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Final Score", f"{sel['final_score']:.2f}")
                    breakdown_df = pd.DataFrame({
                        "Dimension": ["Rules", "Semantic", "Skills", "Career", "Behavioral"],
                        "Score": [
                            sel["rule"].total,
                            sel["emb_sim"] * 100,
                            sel["skills"].total,
                            sel["career"].total,
                            sel["behavioral"].total,
                        ],
                    })
                    st.bar_chart(breakdown_df.set_index("Dimension"))

                with col2:
                    st.markdown("**Reasoning**")
                    st.info(sel["reasoning"])
                    if sel["honeypot"].flags:
                        st.warning("⚠️ Anomaly flags: " + "; ".join(sel["honeypot"].flags))
                    st.markdown("**Redrob Signals**")
                    sig = c.redrob_signals
                    st.write({
                        "Open to work": sig.open_to_work_flag,
                        "Response rate": f"{sig.recruiter_response_rate:.0%}",
                        "Notice period": f"{sig.notice_period_days}d",
                        "GitHub score": sig.github_activity_score,
                        "Interview completion": f"{sig.interview_completion_rate:.0%}",
                    })

    with tab3:
        st.subheader("How the Ranking Works")
        st.markdown("""
This system uses a **3-stage hybrid pipeline**:

**Stage 1 — Rule-Based Pre-Screen**
Fast, deterministic scoring on structured fields: years of experience,
title seniority, skills keyword overlap, and company type (product vs. outsourcing).
Honeypot detection runs here to exclude fraudulent profiles.

**Stage 2 — Semantic Re-Rank**
Sentence-Transformer embeddings (all-MiniLM-L6-v2) compare the full candidate
text against the JD. Skills Trust scoring cross-validates self-declared skills
against endorsements, duration, and platform assessment scores.
Career Trajectory analysis rewards upward progression toward AI/ML.

**Stage 3 — Behavioral Signal Boost**
Redrob platform signals — recruiter response rate, interview completion,
offer acceptance, GitHub activity — reward candidates who convert, not just match.

**Final Score** = weighted sum of all stage signals (configurable in sidebar).
        """)
        st.markdown("---")
        st.markdown("""
**Score Components (configurable via sidebar sliders):**

| Component | Weight | What it measures |
|---|---|---|
| Rules Score | 20% | YoE, title seniority, skills overlap, industry |
| Semantic Match | 25% | Cosine similarity of candidate text vs JD embedding |
| Skills Trust | 20% | Trust-weighted skills: endorsements + assessments + duration |
| Career Trajectory | 15% | Progression pattern, company type, domain convergence |
| Behavioral Signals | 20% | Platform engagement, response rate, GitHub, interview completion |
        """)

    with tab4:
        st.subheader("About This Submission")
        st.markdown("""
**Team:** Refine × Redrob
**Challenge:** Redrob AI — India Runs Data & AI Challenge
**System:** Intelligent Candidate Discovery & Ranking Engine

**Tech Stack:**
- Backend: FastAPI + Python 3.11
- Embeddings: sentence-transformers/all-MiniLM-L6-v2 (offline, CPU)
- Ranking: 3-stage hybrid pipeline (rule-based → semantic → behavioral)
- Frontend: React 18 + TypeScript + Vite + TailwindCSS
- Demo: Streamlit (this app)
- No network calls during ranking — all models run locally

**Key Differentiators:**
- Trust-weighted skills scoring (endorsed + assessment-verified > self-declared)
- Career trajectory analysis (rewards progression toward AI/ML)
- Behavioral twin separation (identical profiles ranked differently by platform signals)
- Full recruiter dashboard UI (most challenge submissions are CLI-only)
        """)


def main():
    st.title("🎯 Redrob AI — Intelligent Candidate Ranker")
    st.caption("Hybrid AI ranking: Rule-Based → Semantic → Behavioral Signals")

    with st.sidebar:
        st.header("Job Description")
        jd_text = st.text_area("Paste JD here", value=load_sample_jd(), height=200)

        st.header("Ranking Weights")
        w_rule = st.slider("Rules (YoE, Title, Skills)", 0, 100, 20)
        w_sem = st.slider("Semantic Match", 0, 100, 25)
        w_skills = st.slider("Skills Trust", 0, 100, 20)
        w_career = st.slider("Career Trajectory", 0, 100, 15)
        w_behav = st.slider("Platform Signals", 0, 100, 20)
        total = w_rule + w_sem + w_skills + w_career + w_behav
        st.metric("Weight Total", f"{total}%", delta=f"{total - 100}%" if total != 100 else None)
        if total != 100:
            st.warning("Weights must sum to 100%")

        run_btn = st.button(
            "🚀 Run Ranking",
            disabled=(total != 100 or not jd_text.strip()),
            type="primary",
            use_container_width=True,
        )

    if run_btn:
        run_ranking(jd_text, {
            "rule_score": w_rule / 100,
            "embedding_similarity": w_sem / 100,
            "skills_trust": w_skills / 100,
            "career_trajectory": w_career / 100,
            "behavioral": w_behav / 100,
        })

    display_results()


if __name__ == "__main__":
    main()
