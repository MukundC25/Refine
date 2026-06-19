"""
ranking.py — Bulk candidate ranking API router.

Exposes POST /rank endpoint that accepts a job description and a JSONL
candidate dataset, runs the RankingEngine, and returns ranked results.

Rate-limited via slowapi. Implementation: Issue 011
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/rank", tags=["ranking"])


@router.post("/")
async def rank_candidates() -> dict:
    """Rank a batch of candidates against a job description.

    Implementation pending (Issue 011).
    """
    raise NotImplementedError("POST /rank — implementation pending (Issue 011)")
