"""
career_analyzer.py — Career trajectory scorer.

Analyses a candidate's employment history to derive trajectory signals:
seniority progression, industry relevance, tenure stability, and recency
of relevant experience.

Implementation: Issue 009
"""

from __future__ import annotations

from typing import Any


class CareerAnalyzer:
    """Score a candidate's career trajectory relative to the target role."""

    def analyze(self, candidate: dict[str, Any], target_role: str) -> dict[str, Any]:
        """Return trajectory signals for *candidate* targeting *target_role*.

        Args:
            candidate: Candidate dict with work history fields.
            target_role: The role title / level being hired for.

        Returns:
            Dict with keys ``seniority_score``, ``industry_relevance``,
            ``tenure_stability``, ``recency_score``, and ``composite``.
        """
        raise NotImplementedError("CareerAnalyzer.analyze() — implementation pending (Issue 009)")
