"""Ranking API router.

POST /rank/prescreen  Stage 1 rule pre-score (no Gemini required).
POST /rank/           Full 3-stage pipeline (pending — Issues 010-013).
"""

from __future__ import annotations

import logging
import re
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.app.core.candidate_loader import validate_candidate
from backend.app.core.jd_parser import ParsedJD
from backend.app.core.rule_scorer import (
    _DEFAULT_PREFERRED_SKILLS,
    _DEFAULT_REQUIRED_SKILLS,
    batch_score,
)
from backend.app.models.schemas import RuleScoreSchema

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/rank", tags=["ranking"])


class PrescreenRequest(BaseModel):
    job_description: str = Field(..., min_length=20)
    candidates: list[dict[str, Any]] = Field(..., min_length=1)
    top_k: int = Field(default=100, ge=1, le=10_000)


class PrescreenResponse(BaseModel):
    total_submitted: int
    total_valid: int
    total_returned: int
    results: list[RuleScoreSchema]


@router.post("/prescreen", response_model=PrescreenResponse, summary="Stage 1 rule pre-screen")
async def prescreen_candidates(request: PrescreenRequest) -> PrescreenResponse:
    """Rule-score a batch of candidate dicts against the supplied JD text.

    Validates each record, drops malformed ones, scores with the rule scorer,
    and returns the top-K sorted by total score descending.
    Uses a keyword-extracted ParsedJD so no GEMINI_API_KEY is required.
    """
    valid_records = [r for raw in request.candidates if (r := validate_candidate(raw)) is not None]
    if not valid_records:
        raise HTTPException(status_code=422, detail="No valid candidate records found.")

    jd = _jd_from_text(request.job_description)
    scores = sorted(batch_score(valid_records, jd), key=lambda s: s.total, reverse=True)
    top = scores[: request.top_k]

    logger.info("prescreen: submitted=%d valid=%d returned=%d",
                len(request.candidates), len(valid_records), len(top))

    return PrescreenResponse(
        total_submitted=len(request.candidates),
        total_valid=len(valid_records),
        total_returned=len(top),
        results=[
            RuleScoreSchema(
                candidate_id=s.candidate_id,
                experience_score=s.experience_score,
                title_score=s.title_score,
                skills_score=s.skills_score,
                industry_score=s.industry_score,
                disqualifier_penalty=s.disqualifier_penalty,
                total=s.total,
            )
            for s in top
        ],
    )


@router.post("/", summary="Full pipeline rank (pending)")
async def rank_candidates() -> dict:
    raise HTTPException(status_code=501, detail="Full pipeline pending. See Issues 010-013.")


def _jd_from_text(text: str) -> ParsedJD:
    """Build a ParsedJD from raw text without calling Gemini."""
    text_lower = text.lower()
    yoe_min, yoe_max = 5.0, 9.0
    if m := re.search(r"(\d+)\s*[-–to]+\s*(\d+)\s*years?", text_lower):
        yoe_min, yoe_max = float(m.group(1)), float(m.group(2))
    elif m := re.search(r"(\d+)\+?\s*years?", text_lower):
        yoe_min = float(m.group(1))
        yoe_max = yoe_min + 4

    return ParsedJD(
        raw_text=text,
        role_title="",
        required_skills=_DEFAULT_REQUIRED_SKILLS,
        preferred_skills=_DEFAULT_PREFERRED_SKILLS,
        disqualifying_signals=[],
        min_years_experience=yoe_min,
        max_years_experience=yoe_max,
        preferred_locations=[],
        notice_period_preference_days=30,
        seniority_level="senior",
        industry_preference="any" if "consulting" in text_lower else "product_company",
        work_mode="hybrid",
        role_embedding_text=text,
        jd_hash="",
        vibe_signals=[],
        hiring_context="",
    )
