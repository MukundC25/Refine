"""
jd_parser.py — Job description → structured requirements parser.

Uses the existing GeminiService to extract structured fields (required skills,
preferred skills, experience level, location constraints, etc.) from raw JD text.

Implementation: Issue 007
"""

from __future__ import annotations

from typing import Any


class JDParser:
    """Parse a raw job description into structured requirement fields."""

    def parse(self, job_description: str) -> dict[str, Any]:
        """Return a structured dict of requirements extracted from *job_description*.

        Keys include (non-exhaustive):
            - ``required_skills``: list[str]
            - ``preferred_skills``: list[str]
            - ``experience_years``: int | None
            - ``location``: str | None
            - ``education_level``: str | None

        Args:
            job_description: Raw JD text.

        Returns:
            Dict of structured requirements.
        """
        raise NotImplementedError("JDParser.parse() — implementation pending (Issue 007)")
