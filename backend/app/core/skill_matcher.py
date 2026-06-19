"""
skill_matcher.py — Semantic skill matcher.

Computes soft skill overlap between a candidate's skill set and the JD's
required/preferred skills using embedding cosine similarity, allowing for
synonyms and related-technology matching (e.g., "PyTorch" ≈ "deep learning").

Implementation: Issue 008
"""

from __future__ import annotations

from typing import Any


class SkillMatcher:
    """Match candidate skills against JD requirements semantically."""

    def match(
        self,
        candidate_skills: list[str],
        required_skills: list[str],
        preferred_skills: list[str] | None = None,
    ) -> dict[str, Any]:
        """Return match scores and aligned skill pairs.

        Args:
            candidate_skills: Skills listed by or inferred from the candidate.
            required_skills: Must-have skills from the parsed JD.
            preferred_skills: Nice-to-have skills from the parsed JD.

        Returns:
            Dict with keys ``required_coverage``, ``preferred_coverage``,
            and ``aligned_pairs`` (list of (candidate_skill, jd_skill, score)).
        """
        raise NotImplementedError("SkillMatcher.match() — implementation pending (Issue 008)")
