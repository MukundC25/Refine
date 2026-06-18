"""
ranking_engine.py — Hybrid ranker orchestrator.

Combines signals from multiple scorers (embedding similarity, skill matching,
career trajectory, behavioural signals) into a final composite rank score.

Implementation: Issue 004
"""

from __future__ import annotations

from typing import Any


class RankingEngine:
    """Orchestrate all sub-scorers and produce a final ranked list."""

    def rank(self, candidates: list[dict[str, Any]], job_description: str) -> list[dict[str, Any]]:
        """Return *candidates* sorted by composite score (descending).

        Args:
            candidates: List of candidate dicts (parsed from JSONL).
            job_description: Raw JD text.

        Returns:
            Candidates with an added ``rank_score`` field, sorted best-first.
        """
        raise NotImplementedError("RankingEngine.rank() — implementation pending (Issue 004)")
