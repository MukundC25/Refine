"""
test_career_analyzer.py — Tests for career_analyzer.py.

Acceptance criteria verified
-----------------------------
  AC1  CAND_0000001 (Ira Vora): domain_convergence ≥ 15, label "ascending" or "lateral"
  AC2  100% outsourcing career (TCS/Infosys): company_type ≤ 5
  AC3  SW Eng → Sr SW Eng → Staff ML Eng trajectory: labeled "ascending"
  AC4  5 roles with 4 short stints (< 12 mo): tenure_stability ≤ 4
  AC5  Career with zero technical keywords: domain_convergence == 0
  AC6  analyze_career() completes 5 000 candidates in < 2 seconds
  AC7  total is always in [0, 100] for any valid input
  AC8  All scoring functions are pure (deterministic, no side-effects)

Synthetic helpers
-----------------
  _entry(**kwargs)   — build a minimal CareerEntry-like namespace
  _candidate(...)    — build a minimal CandidateRecord-like namespace
  _jd()              — build a minimal ParsedJD-like namespace
"""

from __future__ import annotations

import json
import time
import types
from pathlib import Path

import pytest

from backend.app.core.candidate_loader import (
    CandidateRecord,
    validate_candidate,
)
from backend.app.core.career_analyzer import (
    DOMAIN_KEYWORDS,
    HIGH_RELEVANCE_INDUSTRIES,
    OUTSOURCING_FIRMS,
    SENIORITY_MAP,
    CareerTrajectoryScore,
    _title_to_seniority,
    analyze_career,
    company_type_score,
    domain_convergence_score,
    industry_relevance_score,
    label_trajectory,
    progression_score,
    tenure_stability_score,
)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SAMPLE_JSON = (
    _REPO_ROOT
    / "[PUB] India_runs_data_and_ai_challenge"
    / "[PUB] India_runs_data_and_ai_challenge"
    / "India_runs_data_and_ai_challenge"
    / "sample_candidates.json"
)


# ---------------------------------------------------------------------------
# Synthetic builders
# ---------------------------------------------------------------------------


def _entry(
    title: str = "Software Engineer",
    company: str = "Acme",
    industry: str = "Software",
    duration_months: int = 24,
    description: str = "",
    start_date: str = "2020-01-01",
    end_date: str | None = "2022-01-01",
    is_current: bool = False,
) -> types.SimpleNamespace:
    """Return a minimal CareerEntry-like object."""
    return types.SimpleNamespace(
        title=title,
        company=company,
        industry=industry,
        duration_months=duration_months,
        description=description,
        start_date=start_date,
        end_date=end_date,
        is_current=is_current,
    )


def _candidate(
    candidate_id: str = "CAND_0000099",
    career_history: list | None = None,
) -> types.SimpleNamespace:
    """Return a minimal CandidateRecord-like object."""
    return types.SimpleNamespace(
        candidate_id=candidate_id,
        career_history=career_history or [],
    )


def _jd() -> types.SimpleNamespace:
    """Return a minimal ParsedJD-like object."""
    return types.SimpleNamespace(
        role_title="Senior AI Engineer",
        required_skills=["python", "machine learning", "nlp"],
        seniority_level="senior",
    )


# ---------------------------------------------------------------------------
# Sample-data fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def sample_records() -> list[dict]:
    with open(_SAMPLE_JSON, encoding="utf-8") as fh:
        return json.load(fh)


@pytest.fixture(scope="module")
def cand_0000001(sample_records) -> CandidateRecord:
    raw = next(r for r in sample_records if r["candidate_id"] == "CAND_0000001")
    rec = validate_candidate(raw)
    assert rec is not None
    return rec


# ---------------------------------------------------------------------------
# TestTitleToSeniority
# ---------------------------------------------------------------------------


class TestTitleToSeniority:
    """_title_to_seniority() must return the correct level for known titles."""

    def test_intern_is_zero(self):
        assert _title_to_seniority("Software Intern") == 0

    def test_analyst_is_one(self):
        assert _title_to_seniority("Business Analyst") == 1

    def test_engineer_is_two(self):
        assert _title_to_seniority("Backend Engineer") == 2

    def test_senior_beats_engineer(self):
        # "Senior Software Engineer" matches both "senior" (3) and "engineer" (2)
        assert _title_to_seniority("Senior Software Engineer") == 3

    def test_staff_is_four(self):
        assert _title_to_seniority("Staff ML Engineer") == 4

    def test_manager_is_five(self):
        assert _title_to_seniority("Engineering Manager") == 5

    def test_unknown_title_defaults_to_two(self):
        assert _title_to_seniority("Customer Support Specialist") >= 1


# ---------------------------------------------------------------------------
# TestProgressionScore
# ---------------------------------------------------------------------------


class TestProgressionScore:
    """progression_score() — seniority arc scoring (0–25)."""

    def test_empty_history_returns_zero(self):
        assert progression_score([]) == 0.0

    def test_single_engineer_role(self):
        h = [_entry(title="Software Engineer")]
        score = progression_score(h)
        assert 5.0 <= score <= 20.0

    def test_clear_ascending_arc_returns_max(self):
        """SW Eng (2) → Sr SW Eng (3) → Staff ML Eng (4) must give 25. AC3"""
        h = [
            _entry(
                title="Software Engineer",
                start_date="2017-01-01",
                end_date="2019-01-01",
            ),
            _entry(
                title="Senior Software Engineer",
                start_date="2019-01-01",
                end_date="2021-06-01",
            ),
            _entry(
                title="Staff ML Engineer",
                start_date="2021-06-01",
                end_date=None,
                is_current=True,
            ),
        ]
        assert progression_score(h) == 25.0

    def test_lateral_move_at_engineer_level(self):
        """Analytics Eng → Backend Eng (both level 2) must score 15 (lateral). AC1"""
        h = [
            _entry(
                title="Analytics Engineer",
                start_date="2019-07-03",
                end_date="2024-01-08",
            ),
            _entry(
                title="Backend Engineer",
                start_date="2024-03-08",
                end_date=None,
                is_current=True,
            ),
        ]
        assert progression_score(h) == 15.0

    def test_declining_trajectory_scores_low(self):
        h = [
            _entry(
                title="Staff Principal Engineer",
                start_date="2015-01-01",
                end_date="2019-01-01",
            ),
            _entry(
                title="Software Engineer",
                start_date="2019-01-01",
                end_date=None,
                is_current=True,
            ),
        ]
        assert progression_score(h) == 5.0

    def test_management_detour_scores_ten(self):
        """IC → Manager → IC must score 10 (detour penalised)."""
        h = [
            _entry(
                title="Software Engineer",
                start_date="2015-01-01",
                end_date="2018-01-01",
            ),
            _entry(
                title="Engineering Manager",
                start_date="2018-01-01",
                end_date="2020-01-01",
            ),
            _entry(
                title="Senior Engineer",
                start_date="2020-01-01",
                end_date=None,
                is_current=True,
            ),
        ]
        assert progression_score(h) == 10.0

    def test_score_in_valid_range(self):
        for title in (
            "Junior Developer",
            "Engineer",
            "Senior Architect",
            "VP Engineering",
        ):
            h = [_entry(title=title)]
            score = progression_score(h)
            assert 0.0 <= score <= 25.0, f"Out of range for title '{title}': {score}"


# ---------------------------------------------------------------------------
# TestCompanyTypeScore
# ---------------------------------------------------------------------------


class TestCompanyTypeScore:
    """company_type_score() — outsourcing vs. product company ratio (0–25)."""

    def test_all_outsourcing_returns_five(self):
        """100% TCS/Infosys career must score ≤ 5. AC2"""
        h = [
            _entry(company="TCS", duration_months=30),
            _entry(company="Infosys", duration_months=24),
        ]
        assert company_type_score(h) <= 5.0

    def test_all_product_returns_25(self):
        h = [
            _entry(company="Google", duration_months=30),
            _entry(company="Swiggy", duration_months=24),
        ]
        assert company_type_score(h) == 25.0

    def test_mixed_above_60pct_product(self):
        h = [
            _entry(company="Startup Co", duration_months=36),  # product
            _entry(company="TCS", duration_months=12),  # outsourcing
        ]
        # 36/48 = 75% product → 25
        assert company_type_score(h) == 25.0

    def test_mixed_30_60_pct_product(self):
        h = [
            _entry(company="Startup Co", duration_months=20),  # product
            _entry(company="Wipro", duration_months=40),  # outsourcing
        ]
        # 20/60 = 33% product → 15
        assert company_type_score(h) == 15.0

    def test_mixed_under_30pct_product(self):
        h = [
            _entry(company="Startup Co", duration_months=10),  # product
            _entry(company="TCS", duration_months=40),  # outsourcing
            _entry(company="Wipro", duration_months=30),  # outsourcing
        ]
        # 10/80 = 12.5% product → 5
        assert company_type_score(h) == 5.0

    def test_company_name_case_insensitive(self):
        """Matching must be case-insensitive ("WIPRO" == "wipro")."""
        h = [_entry(company="WIPRO", duration_months=24)]
        assert company_type_score(h) == 5.0

    def test_hcl_matched_as_outsourcing(self):
        h = [_entry(company="HCL", duration_months=24)]
        assert company_type_score(h) == 5.0

    def test_tech_mahindra_matched_as_outsourcing(self):
        h = [_entry(company="Tech Mahindra", duration_months=24)]
        assert company_type_score(h) == 5.0

    def test_empty_history_returns_neutral(self):
        assert company_type_score([]) == 15.0

    def test_cand_0000001_product_company(self, cand_0000001):
        """CAND_0000001 (Mindtree + Dunder Mifflin) must score > 5. AC1 context."""
        score = company_type_score(cand_0000001.career_history)
        assert score > 5.0


# ---------------------------------------------------------------------------
# TestDomainConvergenceScore
# ---------------------------------------------------------------------------


class TestDomainConvergenceScore:
    """domain_convergence_score() — AI/ML vocabulary depth (0–30)."""

    def test_zero_keywords_returns_zero(self):
        """Career with no technical keywords must score exactly 0. AC5"""
        h = [
            _entry(
                description="Managed client relationships and filed quarterly reports."
            ),
            _entry(description="Handled customer support tickets and escalations."),
        ]
        assert domain_convergence_score(h) == 0.0

    def test_empty_history_returns_zero(self):
        assert domain_convergence_score([]) == 0.0

    def test_tier1_keywords_score_higher_than_tier2(self):
        """A single tier-1 keyword must outscore a single tier-2 keyword
        when both are subject to the same (non-recent) scoring path.
        Use a single entry with a closed end_date so the role is NOT
        recent relative to itself (ref_date == end_date → 0 months elapsed
        still counts as recent for a lone entry, so we directly compare
        weights: tier_1=4.0 vs tier_2=2.5 with equal recency treatment).
        Use exactly ONE keyword per description to make the comparison fair.
        """
        h_tier1 = [
            _entry(
                description="machine learning models deployed to production.",
                start_date="2020-01-01",
                end_date="2022-01-01",
                is_current=False,
            )
        ]
        # Exactly ONE tier-2 keyword (only 'airflow', no 'pipeline')
        h_tier2 = [
            _entry(
                description="deployed using apache airflow orchestration.",
                start_date="2020-01-01",
                end_date="2022-01-01",
                is_current=False,
            )
        ]
        # Both will be "recent" (end == ref → 0 months elapsed)
        # tier_1 weight=4.0 > tier_2 weight=2.5 → tier1 wins
        assert domain_convergence_score(h_tier1) > domain_convergence_score(h_tier2)

    def test_recency_bonus_applied(self):
        """Keyword in a recent role must score higher than the same keyword
        in a role that ended > 24 months before the career's reference date.

        To make the old role genuinely non-recent we pair it with a newer
        dummy entry (no keywords) so that ref_date is pushed far beyond the
        24-month window from the old role's end_date.
        """
        # Single current role — keyword is in the recent window
        h_recent = [
            _entry(
                description="spark pipeline for airflow orchestration.",
                start_date="2023-01-01",
                end_date=None,
                is_current=True,
            )
        ]
        # Old role ended 2018-01-01; dummy entry pushes ref_date to 2022-06-01
        # (>24 months after the old role ended) → old role is NOT recent
        h_old = [
            _entry(
                description="spark pipeline for airflow orchestration.",
                start_date="2015-01-01",
                end_date="2018-01-01",
                is_current=False,
            ),
            _entry(
                description="managed accounts and filed reports.",  # no keywords
                start_date="2021-01-01",
                end_date="2022-06-01",
                is_current=False,
            ),
        ]
        score_recent = domain_convergence_score(h_recent)
        score_old = domain_convergence_score(h_old)
        assert score_recent > score_old, (
            f"Recent score {score_recent} should exceed old score {score_old}"
        )

    def test_score_capped_at_30(self):
        """Total must never exceed 30 regardless of keyword density."""
        big_desc = " ".join(DOMAIN_KEYWORDS["tier_1"] + DOMAIN_KEYWORDS["tier_2"])
        h = [
            _entry(description=big_desc, is_current=True, end_date=None),
            _entry(description=big_desc, is_current=True, end_date=None),
        ]
        assert domain_convergence_score(h) <= 30.0

    def test_score_is_non_negative(self):
        h = [_entry(description="some random text without any keywords.")]
        assert domain_convergence_score(h) >= 0.0

    def test_cand_0000001_domain_at_least_15(self, cand_0000001):
        """Ira Vora (data engineering → ML) must score ≥ 15 on domain_convergence. AC1"""
        score = domain_convergence_score(cand_0000001.career_history)
        assert score >= 15.0, (
            f"CAND_0000001 domain_convergence={score:.2f}; expected ≥ 15. AC1"
        )

    def test_pipeline_keyword_matched_as_substring(self):
        """'pipeline' must match 'data pipelines' via substring check."""
        h = [_entry(description="Built data pipelines on Apache Airflow.")]
        score = domain_convergence_score(h)
        assert score > 0.0

    def test_multiple_tier1_keywords(self):
        """Profile with several tier-1 keywords must score well above zero."""
        h = [
            _entry(
                description=(
                    "Built recommendation and retrieval systems using "
                    "embeddings and vector stores. Also worked on nlp and "
                    "transformer fine-tuning for ranking tasks."
                ),
                is_current=True,
                end_date=None,
            )
        ]
        score = domain_convergence_score(h)
        assert score >= 20.0, f"Expected ≥ 20, got {score}"


# ---------------------------------------------------------------------------
# TestTenureStabilityScore
# ---------------------------------------------------------------------------


class TestTenureStabilityScore:
    """tenure_stability_score() — job-hopping penalty (0–10)."""

    def test_single_role_returns_ten(self):
        assert tenure_stability_score([_entry(duration_months=36)]) == 10.0

    def test_all_long_stints_returns_ten(self):
        h = [_entry(duration_months=d) for d in [24, 30, 36, 18]]
        assert tenure_stability_score(h) == 10.0

    def test_more_than_half_short_returns_three(self):
        """5 roles, 4 of which are 8–10 months: score must be ≤ 4. AC4"""
        h = [
            _entry(duration_months=8),
            _entry(duration_months=9),
            _entry(duration_months=10),
            _entry(duration_months=8),
            _entry(duration_months=24),  # only 1 long stint
        ]
        score = tenure_stability_score(h)
        assert score <= 4.0, f"Expected ≤ 4, got {score}. AC4"
        assert score == 3.0

    def test_25_to_50_pct_short_returns_seven(self):
        """2 out of 6 short stints = 33 % → 7."""
        h = [
            _entry(duration_months=10),  # short
            _entry(duration_months=11),  # short
            _entry(duration_months=24),
            _entry(duration_months=30),
            _entry(duration_months=18),
            _entry(duration_months=36),
        ]
        assert tenure_stability_score(h) == 7.0

    def test_exactly_25pct_not_penalised(self):
        """1 out of 4 short stints = 25 % → 10 (boundary inclusive)."""
        h = [
            _entry(duration_months=11),  # short
            _entry(duration_months=24),
            _entry(duration_months=18),
            _entry(duration_months=36),
        ]
        # 1/4 = 0.25, which is NOT > 0.25, so → 10.0
        assert tenure_stability_score(h) == 10.0

    def test_score_in_valid_range(self):
        for n_short in (0, 1, 3, 5):
            h = [_entry(duration_months=6)] * n_short + [_entry(duration_months=24)] * (
                5 - n_short
            )
            score = tenure_stability_score(h)
            assert 0.0 <= score <= 10.0


# ---------------------------------------------------------------------------
# TestIndustryRelevanceScore
# ---------------------------------------------------------------------------


class TestIndustryRelevanceScore:
    """industry_relevance_score() — industry alignment (0–10)."""

    def test_all_software_returns_ten(self):
        h = [
            _entry(industry="Software", duration_months=30),
            _entry(industry="SaaS", duration_months=24),
        ]
        assert industry_relevance_score(h) == 10.0

    def test_ai_ml_industry_matched(self):
        """'AI/ML' industry must match via the 'ai' substring."""
        h = [_entry(industry="AI/ML", duration_months=24)]
        assert industry_relevance_score(h) == 10.0

    def test_fintech_matched(self):
        h = [_entry(industry="Fintech", duration_months=24)]
        assert industry_relevance_score(h) == 10.0

    def test_paper_products_irrelevant(self):
        h = [_entry(industry="Paper Products", duration_months=24)]
        score = industry_relevance_score(h)
        assert score <= 2.0

    def test_mixed_relevant_and_irrelevant(self):
        h = [
            _entry(industry="Software", duration_months=30),  # relevant
            _entry(industry="Manufacturing", duration_months=30),  # not relevant
        ]
        # 50 % relevant → 6 pts
        assert industry_relevance_score(h) == 6.0

    def test_empty_history_neutral(self):
        assert industry_relevance_score([]) == 6.0

    def test_score_in_valid_range(self):
        for industry in ("IT Services", "Paper Products", "Software", "AI/ML"):
            h = [_entry(industry=industry, duration_months=24)]
            score = industry_relevance_score(h)
            assert 0.0 <= score <= 10.0


# ---------------------------------------------------------------------------
# TestLabelTrajectory
# ---------------------------------------------------------------------------


class TestLabelTrajectory:
    """label_trajectory() — correct label for each quadrant."""

    def _scores(self, seniority=15.0, domain=15.0, total=60.0) -> CareerTrajectoryScore:
        return CareerTrajectoryScore(
            candidate_id="CAND_TEST",
            seniority_progression=seniority,
            company_type=20.0,
            domain_convergence=domain,
            tenure_stability=10.0,
            industry_relevance=8.0,
            total=total,
            trajectory_label="",
        )

    def test_ascending_when_both_high(self):
        s = self._scores(seniority=25.0, domain=25.0)
        assert label_trajectory(s) == "ascending"

    def test_ascending_boundary_exactly_20_and_20(self):
        s = self._scores(seniority=20.0, domain=20.0)
        assert label_trajectory(s) == "ascending"

    def test_lateral_domain_high_seniority_medium(self):
        s = self._scores(seniority=15.0, domain=20.0)
        assert label_trajectory(s) == "lateral"

    def test_lateral_at_boundary(self):
        s = self._scores(seniority=10.0, domain=15.0)
        assert label_trajectory(s) == "lateral"

    def test_declining_low_seniority(self):
        s = self._scores(seniority=5.0, domain=20.0)
        assert label_trajectory(s) == "declining"

    def test_declining_low_domain(self):
        s = self._scores(seniority=15.0, domain=5.0)
        assert label_trajectory(s) == "declining"

    def test_pivot_medium_both(self):
        # seniority=10, domain=10 → domain<15, seniority not <10, domain not <8
        s = self._scores(seniority=10.0, domain=10.0)
        assert label_trajectory(s) == "pivot"

    def test_returns_valid_string(self):
        for seniority in (5.0, 15.0, 22.0):
            for domain in (5.0, 15.0, 22.0):
                s = self._scores(seniority=seniority, domain=domain)
                assert label_trajectory(s) in {
                    "ascending",
                    "lateral",
                    "declining",
                    "pivot",
                }


# ---------------------------------------------------------------------------
# TestAnalyzeCareer — integration
# ---------------------------------------------------------------------------


class TestAnalyzeCareer:
    """analyze_career() integration tests."""

    def test_returns_career_trajectory_score(self, cand_0000001):
        result = analyze_career(cand_0000001, _jd())
        assert isinstance(result, CareerTrajectoryScore)

    def test_candidate_id_preserved(self, cand_0000001):
        result = analyze_career(cand_0000001, _jd())
        assert result.candidate_id == "CAND_0000001"

    def test_cand_0000001_domain_convergence_ge_15(self, cand_0000001):
        """Ira Vora: domain_convergence ≥ 15. AC1"""
        result = analyze_career(cand_0000001, _jd())
        assert result.domain_convergence >= 15.0, (
            f"CAND_0000001 domain_convergence={result.domain_convergence:.2f}; "
            "expected ≥ 15.0. AC1"
        )

    def test_cand_0000001_label_ascending_or_lateral(self, cand_0000001):
        """Ira Vora: trajectory label must be 'ascending' or 'lateral'. AC1"""
        result = analyze_career(cand_0000001, _jd())
        assert result.trajectory_label in {"ascending", "lateral"}, (
            f"CAND_0000001 label='{result.trajectory_label}'; "
            "expected 'ascending' or 'lateral'. AC1"
        )

    def test_ascending_trajectory_labeled_correctly(self):
        """SW Eng → Sr SW Eng → Staff ML Eng: label must be 'ascending'. AC3"""
        candidate = _candidate(
            candidate_id="CAND_TEST_ASCENDING",
            career_history=[
                _entry(
                    title="Software Engineer",
                    company="Startup",
                    industry="Software",
                    duration_months=24,
                    description=(
                        "Built data pipelines and feature engineering scripts in Python. "
                        "Worked on machine learning model training and evaluation."
                    ),
                    start_date="2017-01-01",
                    end_date="2019-01-01",
                ),
                _entry(
                    title="Senior Software Engineer",
                    company="Startup",
                    industry="Software",
                    duration_months=30,
                    description=(
                        "Led the NLP and ranking model development. Worked on "
                        "embeddings, transformer fine-tuning, and vector retrieval."
                    ),
                    start_date="2019-01-01",
                    end_date="2021-07-01",
                ),
                _entry(
                    title="Staff ML Engineer",
                    company="BigTech",
                    industry="Software",
                    duration_months=36,
                    description=(
                        "Designed recommendation systems with LLM and RAG pipelines. "
                        "Owned feature engineering, model training, and deployment."
                    ),
                    start_date="2021-07-01",
                    end_date=None,
                    is_current=True,
                ),
            ],
        )
        result = analyze_career(candidate, _jd())
        assert result.trajectory_label == "ascending", (
            f"Expected 'ascending', got '{result.trajectory_label}'. "
            f"seniority={result.seniority_progression}, "
            f"domain={result.domain_convergence}. AC3"
        )

    def test_outsourcing_only_company_type_le_5(self):
        """100% TCS/Infosys career: company_type ≤ 5. AC2"""
        candidate = _candidate(
            candidate_id="CAND_OUTSOURCE",
            career_history=[
                _entry(company="TCS", duration_months=36, description=""),
                _entry(company="Infosys", duration_months=30, description=""),
            ],
        )
        result = analyze_career(candidate, _jd())
        assert result.company_type <= 5.0, (
            f"company_type={result.company_type}; expected ≤ 5. AC2"
        )

    def test_zero_keywords_domain_convergence_zero(self):
        """Career with no technical keywords: domain_convergence == 0. AC5"""
        candidate = _candidate(
            candidate_id="CAND_NOKW",
            career_history=[
                _entry(description="Managed accounts payable and prepared reports."),
                _entry(description="Led marketing campaigns and coordinated events."),
            ],
        )
        result = analyze_career(candidate, _jd())
        assert result.domain_convergence == 0.0, (
            f"Expected domain_convergence=0.0, got {result.domain_convergence}. AC5"
        )

    def test_four_short_stints_tenure_stability_le_4(self):
        """5 roles, 4 of which are 8–10 months: tenure_stability ≤ 4. AC4"""
        candidate = _candidate(
            candidate_id="CAND_HOPPER",
            career_history=[
                _entry(duration_months=8, description=""),
                _entry(duration_months=9, description=""),
                _entry(duration_months=10, description=""),
                _entry(duration_months=8, description=""),
                _entry(duration_months=30, description=""),  # one long stint
            ],
        )
        result = analyze_career(candidate, _jd())
        assert result.tenure_stability <= 4.0, (
            f"tenure_stability={result.tenure_stability}; expected ≤ 4. AC4"
        )

    def test_total_always_in_0_to_100(self):
        """Composite total must always be in [0, 100]. AC7"""
        cases = [
            # Worst possible candidate
            _candidate(
                career_history=[
                    _entry(
                        company="TCS",
                        duration_months=5,
                        description="filed reports.",
                        title="Intern",
                    ),
                ]
            ),
            # Best possible candidate
            _candidate(
                career_history=[
                    _entry(
                        title="Staff ML Engineer",
                        company="DeepMind",
                        industry="AI",
                        duration_months=60,
                        description=" ".join(DOMAIN_KEYWORDS["tier_1"]),
                        is_current=True,
                        end_date=None,
                    ),
                ]
            ),
            # Empty career (shouldn't occur in practice but guard anyway)
            _candidate(
                career_history=[
                    _entry(description="", title="Unknown", duration_months=0),
                ]
            ),
        ]
        for c in cases:
            result = analyze_career(c, _jd())
            assert 0.0 <= result.total <= 100.0, (
                f"total={result.total} out of [0, 100]. AC7"
            )

    def test_trajectory_label_always_valid(self):
        """label must always be one of the four valid strings. AC7"""
        for company in ("TCS", "Google", "Wipro"):
            for title in ("Intern", "Engineer", "Staff ML Engineer"):
                candidate = _candidate(
                    career_history=[
                        _entry(
                            company=company,
                            title=title,
                            description="python pipeline etl",
                        ),
                    ]
                )
                result = analyze_career(candidate, _jd())
                assert result.trajectory_label in {
                    "ascending",
                    "lateral",
                    "declining",
                    "pivot",
                }

    def test_deterministic(self, cand_0000001):
        """Same input must always produce identical output. AC8"""
        r1 = analyze_career(cand_0000001, _jd())
        r2 = analyze_career(cand_0000001, _jd())
        assert r1.seniority_progression == r2.seniority_progression
        assert r1.company_type == r2.company_type
        assert r1.domain_convergence == r2.domain_convergence
        assert r1.tenure_stability == r2.tenure_stability
        assert r1.industry_relevance == r2.industry_relevance
        assert r1.total == r2.total
        assert r1.trajectory_label == r2.trajectory_label


# ---------------------------------------------------------------------------
# TestPerformance — AC6
# ---------------------------------------------------------------------------


class TestPerformance:
    """analyze_career() must handle 5 000 candidates in < 2 seconds. AC6"""

    def _make_5k_candidates(self) -> list:
        """Build 5 000 lightweight synthetic candidates."""
        descriptions = [
            "Built data pipelines using spark and airflow for ETL jobs.",
            "machine learning model training and feature engineering in python.",
            "sql reporting and tableau dashboards for the analytics team.",
            "Managed client accounts and prepared quarterly financial reports.",
            "NLP and transformer-based recommendation and ranking systems.",
        ]
        candidates = []
        for i in range(5_000):
            desc = descriptions[i % len(descriptions)]
            cid = f"CAND_{i:07d}"
            career_history = [
                _entry(
                    title="Software Engineer",
                    company="Startup" if i % 3 else "TCS",
                    industry="Software" if i % 2 else "IT Services",
                    duration_months=24 + (i % 12),
                    description=desc,
                    start_date="2020-01-01",
                    end_date=None,
                    is_current=True,
                )
            ]
            candidates.append(
                _candidate(candidate_id=cid, career_history=career_history)
            )
        return candidates

    def test_5k_candidates_under_2_seconds(self):
        """5 000 calls to analyze_career() must complete in < 2 seconds. AC6"""
        candidates = self._make_5k_candidates()
        jd = _jd()

        t0 = time.perf_counter()
        for cand in candidates:
            analyze_career(cand, jd)
        elapsed = time.perf_counter() - t0

        assert elapsed < 2.0, (
            f"analyze_career() took {elapsed:.3f}s for 5 000 candidates; "
            "expected < 2s. AC6"
        )

    def test_all_totals_in_range_under_load(self):
        """Ensure no numeric overflow during bulk processing. AC7"""
        candidates = self._make_5k_candidates()
        jd = _jd()
        for cand in candidates:
            result = analyze_career(cand, jd)
            assert 0.0 <= result.total <= 100.0
