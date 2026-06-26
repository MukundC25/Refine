"""
test_candidate_loader.py — Unit tests for candidate_loader.py.

Covers:
  - stream_candidates()       — all 5 sample records parse correctly
  - load_candidates_batched() — batch boundaries respected
  - load_all_candidates()     — convenience loader
  - validate_candidate()      — rejects missing required fields
  - build_candidate_text()    — non-empty, meaningful output for every sample
  - gzip support              — transparent .jsonl.gz handling
"""

from __future__ import annotations

import gzip
import json
import os
import pathlib
import tempfile

import pytest

from backend.app.core.candidate_loader import (
    CandidateRecord,
    build_candidate_text,
    load_all_candidates,
    load_candidates_batched,
    stream_candidates,
    validate_candidate,
)

# ---------------------------------------------------------------------------
# Path to the sample file provided with the challenge dataset
# ---------------------------------------------------------------------------

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]  # .../Downloads
_SAMPLE_JSON = (
    _REPO_ROOT
    / "[PUB] India_runs_data_and_ai_challenge"
    / "India_runs_data_and_ai_challenge"
    / "sample_candidates.json"
)

# ---------------------------------------------------------------------------
# Fixtures — write sample data to a temp .jsonl and .jsonl.gz
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def sample_records_raw() -> list[dict]:
    """Load the raw dicts from sample_candidates.json."""
    with open(_SAMPLE_JSON, encoding="utf-8") as fh:
        data = json.load(fh)
    assert isinstance(data, list), "sample_candidates.json must be a JSON array"
    return data


@pytest.fixture(scope="module")
def tmp_jsonl(sample_records_raw, tmp_path_factory) -> str:
    """Write sample records as a .jsonl file and return its path."""
    p = tmp_path_factory.mktemp("data") / "sample.jsonl"
    with open(p, "w", encoding="utf-8") as fh:
        for rec in sample_records_raw:
            fh.write(json.dumps(rec) + "\n")
    return str(p)


@pytest.fixture(scope="module")
def tmp_jsonl_gz(sample_records_raw, tmp_path_factory) -> str:
    """Write sample records as a .jsonl.gz file and return its path."""
    p = tmp_path_factory.mktemp("data") / "sample.jsonl.gz"
    with gzip.open(p, "wb") as fh:
        for rec in sample_records_raw:
            fh.write((json.dumps(rec) + "\n").encode())
    return str(p)


# ---------------------------------------------------------------------------
# stream_candidates
# ---------------------------------------------------------------------------

class TestStreamCandidates:
    def test_yields_all_five_records(self, tmp_jsonl, sample_records_raw):
        records = list(stream_candidates(tmp_jsonl))
        assert len(records) == len(sample_records_raw)

    def test_returns_candidate_record_instances(self, tmp_jsonl):
        for rec in stream_candidates(tmp_jsonl):
            assert isinstance(rec, CandidateRecord)

    def test_candidate_ids_match(self, tmp_jsonl, sample_records_raw):
        expected_ids = {r["candidate_id"] for r in sample_records_raw}
        actual_ids = {r.candidate_id for r in stream_candidates(tmp_jsonl)}
        assert actual_ids == expected_ids

    def test_skips_blank_lines(self, tmp_path):
        """Blank lines in the middle of the file must not raise."""
        p = tmp_path / "blank.jsonl"
        valid = {
            "candidate_id": "CAND_9990001",
            "profile": {
                "anonymized_name": "Test User",
                "headline": "Engineer",
                "summary": "Summary here",
                "location": "Delhi",
                "country": "India",
                "years_of_experience": 3.0,
                "current_title": "SWE",
                "current_company": "Acme",
                "current_company_size": "51-200",
                "current_industry": "Software",
            },
            "career_history": [{
                "company": "Acme",
                "title": "SWE",
                "start_date": "2022-01-01",
                "end_date": None,
                "duration_months": 12,
                "is_current": True,
                "industry": "Software",
                "company_size": "51-200",
                "description": "Built things.",
            }],
            "education": [],
            "skills": [],
            "certifications": [],
            "languages": [],
            "redrob_signals": {
                "profile_completeness_score": 70.0,
                "signup_date": "2024-01-01",
                "last_active_date": "2026-01-01",
                "open_to_work_flag": True,
                "profile_views_received_30d": 5,
                "applications_submitted_30d": 1,
                "recruiter_response_rate": 0.5,
                "avg_response_time_hours": 24.0,
                "skill_assessment_scores": {},
                "connection_count": 100,
                "endorsements_received": 10,
                "notice_period_days": 30,
                "expected_salary_range_inr_lpa": {"min": 10.0, "max": 20.0},
                "preferred_work_mode": "remote",
                "willing_to_relocate": False,
                "github_activity_score": 50.0,
                "search_appearance_30d": 20,
                "saved_by_recruiters_30d": 2,
                "interview_completion_rate": 0.8,
                "offer_acceptance_rate": 0.5,
                "verified_email": True,
                "verified_phone": True,
                "linkedin_connected": True,
            },
        }
        p.write_text("\n" + json.dumps(valid) + "\n\n", encoding="utf-8")
        records = list(stream_candidates(str(p)))
        assert len(records) == 1

    def test_skips_malformed_json_line(self, tmp_path):
        """A corrupt JSON line must be skipped, not raise."""
        p = tmp_path / "corrupt.jsonl"
        p.write_text("NOT_VALID_JSON\n", encoding="utf-8")
        records = list(stream_candidates(str(p)))
        assert records == []


# ---------------------------------------------------------------------------
# gzip support
# ---------------------------------------------------------------------------

class TestGzipSupport:
    def test_gz_yields_same_count(self, tmp_jsonl, tmp_jsonl_gz):
        plain = list(stream_candidates(tmp_jsonl))
        compressed = list(stream_candidates(tmp_jsonl_gz))
        assert len(plain) == len(compressed)

    def test_gz_ids_match(self, tmp_jsonl, tmp_jsonl_gz):
        plain_ids = {r.candidate_id for r in stream_candidates(tmp_jsonl)}
        gz_ids = {r.candidate_id for r in stream_candidates(tmp_jsonl_gz)}
        assert plain_ids == gz_ids


# ---------------------------------------------------------------------------
# load_candidates_batched
# ---------------------------------------------------------------------------

class TestLoadCandidatesBatched:
    def test_single_batch_when_small(self, tmp_jsonl, sample_records_raw):
        batches = list(load_candidates_batched(tmp_jsonl, batch_size=512))
        assert len(batches) == 1
        assert len(batches[0]) == len(sample_records_raw)

    def test_batch_size_respected(self, tmp_jsonl, sample_records_raw):
        """With batch_size=2 and 5 records we expect ceil(5/2) = 3 batches."""
        batches = list(load_candidates_batched(tmp_jsonl, batch_size=2))
        n = len(sample_records_raw)
        expected_batches = -(-n // 2)  # ceiling division
        assert len(batches) == expected_batches
        # All records accounted for
        total = sum(len(b) for b in batches)
        assert total == n

    def test_no_empty_batches(self, tmp_jsonl):
        for batch in load_candidates_batched(tmp_jsonl, batch_size=3):
            assert len(batch) > 0

    def test_all_elements_are_candidate_records(self, tmp_jsonl):
        for batch in load_candidates_batched(tmp_jsonl):
            for rec in batch:
                assert isinstance(rec, CandidateRecord)


# ---------------------------------------------------------------------------
# load_all_candidates
# ---------------------------------------------------------------------------

class TestLoadAllCandidates:
    def test_returns_list(self, tmp_jsonl):
        result = load_all_candidates(tmp_jsonl)
        assert isinstance(result, list)

    def test_all_five_records(self, tmp_jsonl, sample_records_raw):
        result = load_all_candidates(tmp_jsonl)
        assert len(result) == len(sample_records_raw)


# ---------------------------------------------------------------------------
# validate_candidate
# ---------------------------------------------------------------------------

class TestValidateCandidate:
    def test_valid_record_parses(self, sample_records_raw):
        for raw in sample_records_raw:
            result = validate_candidate(raw)
            assert result is not None, f"Expected valid parse for {raw.get('candidate_id')}"

    def test_missing_candidate_id_returns_none(self, sample_records_raw):
        bad = {**sample_records_raw[0]}
        del bad["candidate_id"]
        assert validate_candidate(bad) is None

    def test_missing_profile_returns_none(self, sample_records_raw):
        bad = {**sample_records_raw[0]}
        del bad["profile"]
        assert validate_candidate(bad) is None

    def test_missing_career_history_returns_none(self, sample_records_raw):
        bad = {**sample_records_raw[0]}
        del bad["career_history"]
        assert validate_candidate(bad) is None

    def test_empty_career_history_returns_none(self, sample_records_raw):
        bad = {k: v for k, v in sample_records_raw[0].items()}
        bad["career_history"] = []  # violates min_length=1
        assert validate_candidate(bad) is None

    def test_malformed_candidate_id_pattern_returns_none(self, sample_records_raw):
        bad = {**sample_records_raw[0]}
        bad["candidate_id"] = "WRONG_ID"
        assert validate_candidate(bad) is None

    def test_completely_empty_dict_returns_none(self):
        assert validate_candidate({}) is None


# ---------------------------------------------------------------------------
# build_candidate_text
# ---------------------------------------------------------------------------

class TestBuildCandidateText:
    def test_non_empty_for_all_samples(self, sample_records_raw):
        for raw in sample_records_raw:
            record = validate_candidate(raw)
            assert record is not None
            text = build_candidate_text(record)
            assert isinstance(text, str)
            assert len(text.strip()) > 0, f"Empty text for {raw['candidate_id']}"

    def test_contains_headline(self, sample_records_raw):
        raw = sample_records_raw[0]
        record = validate_candidate(raw)
        text = build_candidate_text(record)
        assert raw["profile"]["headline"] in text

    def test_contains_current_title(self, sample_records_raw):
        raw = sample_records_raw[0]
        record = validate_candidate(raw)
        text = build_candidate_text(record)
        assert raw["profile"]["current_title"] in text

    def test_contains_current_company(self, sample_records_raw):
        raw = sample_records_raw[0]
        record = validate_candidate(raw)
        text = build_candidate_text(record)
        assert raw["profile"]["current_company"] in text

    def test_contains_years_of_experience(self, sample_records_raw):
        raw = sample_records_raw[0]
        record = validate_candidate(raw)
        text = build_candidate_text(record)
        assert str(raw["profile"]["years_of_experience"]) in text

    def test_contains_career_description(self, sample_records_raw):
        raw = sample_records_raw[0]
        record = validate_candidate(raw)
        text = build_candidate_text(record)
        # First career entry description must appear somewhere
        first_desc_snippet = raw["career_history"][0]["description"][:40]
        assert first_desc_snippet in text

    def test_pipe_separated_structure(self, sample_records_raw):
        record = validate_candidate(sample_records_raw[0])
        text = build_candidate_text(record)
        assert " | " in text

    def test_expert_skills_included(self, sample_records_raw):
        """For CAND_0000001 which has advanced NLP skill, check it's in output."""
        record = validate_candidate(sample_records_raw[0])
        text = build_candidate_text(record)
        advanced_skills = [s.name for s in record.skills if s.proficiency in ("advanced", "expert")]
        if advanced_skills:
            assert any(skill in text for skill in advanced_skills)

    def test_education_included(self, sample_records_raw):
        raw = sample_records_raw[0]
        record = validate_candidate(raw)
        text = build_candidate_text(record)
        inst = raw["education"][0]["institution"]
        assert inst in text
