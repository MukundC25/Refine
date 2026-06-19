"""
signal_scorer.py — Behavioural signal scorer.

Extracts and scores behavioural signals from candidate profiles such as
response time, platform engagement, and application completeness.

Implementation: Issue 005
"""

from __future__ import annotations

from typing import Any


class SignalScorer:
    """Score behavioural signals extracted from a candidate profile."""

    def score(self, candidate: dict[str, Any]) -> float:
        """Return a normalised signal score in [0, 1].

        Args:
            candidate: Candidate dict with raw profile fields.

        Returns:
            Float score where 1.0 is the strongest positive signal.
        """
        raise NotImplementedError("SignalScorer.score() — implementation pending (Issue 005)")
