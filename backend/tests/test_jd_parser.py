"""
tests/test_jd_parser.py — Unit tests for backend/app/core/jd_parser.py

Run from the repo root:
    python -m pytest backend/tests/test_jd_parser.py -v

These tests are designed to run **without** a live Gemini API key by mocking
the Gemini call.  Integration tests (marked `integration`) are skipped unless
GEMINI_API_KEY is set.
"""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Adjust import path so tests can find the package regardless of cwd
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.app.core.jd_parser import (
    ParsedJD,
    _build_role_embedding_text,
    _md5,
    _safe_float,
    _safe_int,
    _safe_list,
    _safe_str,
    cache_parsed_jd,
    get_or_parse_jd,
    load_cached_jd,
    parse_jd_from_text,
    parse_jd_from_docx,
    parse_jd_from_pdf,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_JD = """
Senior AI Engineer — Redrob

We are looking for a Senior AI Engineer with 5-9 years of experience to join
our product team in Pune or Noida. You will build and own the candidate
ranking pipeline end-to-end.

Required skills:
- Embeddings and vector databases (Pinecone, Weaviate, Qdrant)
- Python (advanced)
- Ranking evaluation frameworks (NDCG, MAP, MRR)
- Production ML deployment experience

Preferred:
- LLM fine-tuning experience
- Learning-to-rank (LTR) algorithms
- HR-tech domain knowledge

We strongly prefer candidates from product companies. Consulting-only
backgrounds are a poor fit. Experience limited to CV/speech models only is
also not aligned with our needs.

Notice period: we prefer candidates who can join within 30 days. Buyout of up
to 30 days is possible.

Work mode: hybrid (2–3 days on-site in Pune/Noida).
Culture: we value shippers over researchers. We are async-first and
writing-heavy. If you prefer meetings over docs, this is not the role for you.
"""

MINIMAL_EXTRACTED = {
    "role_title": "Senior AI Engineer",
    "required_skills": ["embeddings", "vector databases", "python", "ranking evaluation"],
    "preferred_skills": ["LLM fine-tuning", "learning-to-rank", "HR-tech"],
    "disqualifying_signals": [
        "consulting-only background",
        "CV/speech-only ML experience",
        "no production deployment experience",
    ],
    "min_years_experience": 5.0,
    "max_years_experience": 9.0,
    "preferred_locations": ["Pune", "Noida"],
    "notice_period_preference_days": 30,
    "seniority_level": "senior",
    "industry_preference": "product_company",
    "work_mode": "hybrid",
    "vibe_signals": ["shipper > researcher", "async-first", "writing-heavy"],
}


def _make_parsed_jd(**overrides) -> ParsedJD:
    """Return a minimal valid ParsedJD, optionally overriding fields."""
    data = dict(
        raw_text=SAMPLE_JD,
        role_title="Senior AI Engineer",
        required_skills=["embeddings", "vector databases", "python"],
        preferred_skills=["LLM fine-tuning"],
        disqualifying_signals=["consulting-only"],
        min_years_experience=5.0,
        max_years_experience=9.0,
        preferred_locations=["Pune", "Noida"],
        notice_period_preference_days=30,
        seniority_level="senior",
        industry_preference="product_company",
        work_mode="hybrid",
        role_embedding_text="A senior AI engineer role requiring embeddings and vector DB expertise.",
        jd_hash=_md5(SAMPLE_JD),
        vibe_signals=["shipper > researcher"],
        hiring_context="",
    )
    data.update(overrides)
    return ParsedJD(**data)


# ---------------------------------------------------------------------------
# Helper / utility tests
# ---------------------------------------------------------------------------

class TestHelpers:
    def test_md5_is_deterministic(self):
        assert _md5("hello") == _md5("hello")

    def test_md5_differs_for_different_input(self):
        assert _md5("hello") != _md5("world")

    def test_md5_hex_length(self):
        assert len(_md5("any string")) == 32

    @pytest.mark.parametrize("value,expected", [
        (["a", "b"], ["a", "b"]),
        (None, []),
        ("not a list", []),
        ([], []),
        ([1, 2, 3], ["1", "2", "3"]),
    ])
    def test_safe_list(self, value, expected):
        assert _safe_list(value) == expected

    @pytest.mark.parametrize("value,default,expected", [
        (3.5, 0.0, 3.5),
        ("7", 0.0, 7.0),
        (None, 1.5, 1.5),
        ("not-a-number", 2.0, 2.0),
    ])
    def test_safe_float(self, value, default, expected):
        assert _safe_float(value, default) == expected

    @pytest.mark.parametrize("value,default,expected", [
        (5, 0, 5),
        ("30", 0, 30),
        (None, 7, 7),
        ("x", 0, 0),
    ])
    def test_safe_int(self, value, default, expected):
        assert _safe_int(value, default) == expected

    @pytest.mark.parametrize("value,default,expected", [
        ("hello", "", "hello"),
        (None, "fallback", "fallback"),
        ("", "fallback", "fallback"),
        (42, "", "42"),
    ])
    def test_safe_str(self, value, default, expected):
        assert _safe_str(value, default) == expected


# ---------------------------------------------------------------------------
# _build_role_embedding_text (no Gemini)
# ---------------------------------------------------------------------------

class TestBuildRoleEmbeddingText:
    def test_returns_non_empty_string(self):
        with patch(
            "backend.app.core.jd_parser._generate_embedding_text_with_gemini",
            return_value="",
        ):
            result = _build_role_embedding_text(MINIMAL_EXTRACTED)
        assert isinstance(result, str)
        assert len(result) > 20

    def test_includes_role_title(self):
        with patch(
            "backend.app.core.jd_parser._generate_embedding_text_with_gemini",
            return_value="",
        ):
            result = _build_role_embedding_text(MINIMAL_EXTRACTED)
        assert "Senior AI Engineer" in result

    def test_uses_gemini_output_when_available(self):
        rich_text = "A richly generated paragraph for embedding."
        with patch(
            "backend.app.core.jd_parser._generate_embedding_text_with_gemini",
            return_value=rich_text,
        ):
            result = _build_role_embedding_text(MINIMAL_EXTRACTED)
        assert result == rich_text

    def test_fallback_on_empty_dict(self):
        with patch(
            "backend.app.core.jd_parser._generate_embedding_text_with_gemini",
            return_value="",
        ):
            result = _build_role_embedding_text({})
        # Should not raise; may return empty or minimal string
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# parse_jd_from_text (Gemini mocked)
# ---------------------------------------------------------------------------

class TestParseJdFromText:
    def _mock_gemini_calls(self, extracted_dict: dict, embedding_text: str = "Mocked embedding."):
        """Context manager patching both Gemini calls."""
        return patch.multiple(
            "backend.app.core.jd_parser",
            _extract_with_gemini=MagicMock(return_value=extracted_dict),
            _generate_embedding_text_with_gemini=MagicMock(return_value=embedding_text),
        )

    def test_returns_parsed_jd_instance(self):
        with self._mock_gemini_calls(MINIMAL_EXTRACTED):
            result = parse_jd_from_text(SAMPLE_JD)
        assert isinstance(result, ParsedJD)

    def test_role_title_populated(self):
        with self._mock_gemini_calls(MINIMAL_EXTRACTED):
            result = parse_jd_from_text(SAMPLE_JD)
        assert result.role_title == "Senior AI Engineer"

    def test_required_skills_include_mandatory(self):
        with self._mock_gemini_calls(MINIMAL_EXTRACTED):
            result = parse_jd_from_text(SAMPLE_JD)
        mandatory = {"embeddings", "vector databases", "python", "ranking evaluation"}
        actual = {s.lower() for s in result.required_skills}
        assert mandatory.issubset(actual)

    def test_disqualifying_signals_captured(self):
        with self._mock_gemini_calls(MINIMAL_EXTRACTED):
            result = parse_jd_from_text(SAMPLE_JD)
        signals_lower = [s.lower() for s in result.disqualifying_signals]
        assert any("consult" in s for s in signals_lower)
        assert any("cv" in s or "speech" in s for s in signals_lower)

    def test_experience_range(self):
        with self._mock_gemini_calls(MINIMAL_EXTRACTED):
            result = parse_jd_from_text(SAMPLE_JD)
        assert result.min_years_experience == 5.0
        assert result.max_years_experience == 9.0

    def test_notice_period(self):
        with self._mock_gemini_calls(MINIMAL_EXTRACTED):
            result = parse_jd_from_text(SAMPLE_JD)
        assert result.notice_period_preference_days == 30

    def test_jd_hash_is_md5(self):
        with self._mock_gemini_calls(MINIMAL_EXTRACTED):
            result = parse_jd_from_text(SAMPLE_JD)
        assert result.jd_hash == _md5(SAMPLE_JD)

    def test_jd_hash_deterministic(self):
        with self._mock_gemini_calls(MINIMAL_EXTRACTED):
            r1 = parse_jd_from_text(SAMPLE_JD)
            r2 = parse_jd_from_text(SAMPLE_JD)
        assert r1.jd_hash == r2.jd_hash

    def test_empty_text_raises_value_error(self):
        with pytest.raises(ValueError, match="empty"):
            parse_jd_from_text("")

    def test_whitespace_only_raises_value_error(self):
        with pytest.raises(ValueError, match="empty"):
            parse_jd_from_text("   \n\t  ")

    def test_partial_gemini_output_no_keyerror(self):
        """Partial Gemini output (missing fields) must not raise KeyError."""
        partial = {"role_title": "AI Engineer", "required_skills": ["python"]}
        with self._mock_gemini_calls(partial, embedding_text=""):
            result = parse_jd_from_text(SAMPLE_JD)
        # Defaults applied
        assert result.preferred_skills == []
        assert result.disqualifying_signals == []
        assert result.min_years_experience == 0.0
        assert result.notice_period_preference_days == 30

    def test_empty_gemini_output_no_crash(self):
        """Completely empty Gemini output must not raise."""
        with self._mock_gemini_calls({}, embedding_text=""):
            result = parse_jd_from_text(SAMPLE_JD)
        assert isinstance(result, ParsedJD)
        assert result.role_title == "Unknown Role"


# ---------------------------------------------------------------------------
# parse_jd_from_docx
# ---------------------------------------------------------------------------

class TestParseJdFromDocx:
    def test_file_not_found_raises(self):
        with pytest.raises(FileNotFoundError):
            parse_jd_from_docx("/nonexistent/path/jd.docx")

    def test_parses_docx_correctly(self, tmp_path):
        try:
            from docx import Document
        except ImportError:
            pytest.skip("python-docx not installed")

        # Create a minimal docx
        doc_path = tmp_path / "jd.docx"
        doc = Document()
        for line in SAMPLE_JD.strip().splitlines():
            if line.strip():
                doc.add_paragraph(line)
        doc.save(str(doc_path))

        with patch.multiple(
            "backend.app.core.jd_parser",
            _extract_with_gemini=MagicMock(return_value=MINIMAL_EXTRACTED),
            _generate_embedding_text_with_gemini=MagicMock(return_value="embedding text"),
        ):
            result = parse_jd_from_docx(str(doc_path))

        assert isinstance(result, ParsedJD)
        assert "Senior AI Engineer" in result.role_title


# ---------------------------------------------------------------------------
# parse_jd_from_pdf
# ---------------------------------------------------------------------------

class TestParseJdFromPdf:
    def test_file_not_found_raises(self):
        with pytest.raises(FileNotFoundError):
            parse_jd_from_pdf("/nonexistent/path/jd.pdf")

    def test_parses_pdf_correctly(self, tmp_path):
        pytest.importorskip("pypdf")
        pytest.importorskip("reportlab")

        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas

        pdf_path = tmp_path / "jd.pdf"
        c = canvas.Canvas(str(pdf_path), pagesize=A4)
        c.drawString(72, 750, "Senior AI Engineer — Redrob")
        c.drawString(72, 720, "Required: Python, embeddings, vector databases")
        c.save()

        with patch.multiple(
            "backend.app.core.jd_parser",
            _extract_with_gemini=MagicMock(return_value=MINIMAL_EXTRACTED),
            _generate_embedding_text_with_gemini=MagicMock(return_value="embedding"),
        ):
            result = parse_jd_from_pdf(str(pdf_path))

        assert isinstance(result, ParsedJD)


# ---------------------------------------------------------------------------
# Caching
# ---------------------------------------------------------------------------

class TestCaching:
    def test_cache_and_load_roundtrip(self, tmp_path):
        cache_file = str(tmp_path / "parsed_jd.json")
        original = _make_parsed_jd()
        cache_parsed_jd(original, cache_file)
        loaded = load_cached_jd(cache_file)

        assert loaded is not None
        assert loaded.jd_hash == original.jd_hash
        assert loaded.role_title == original.role_title
        assert loaded.required_skills == original.required_skills

    def test_load_nonexistent_returns_none(self, tmp_path):
        result = load_cached_jd(str(tmp_path / "missing.json"))
        assert result is None

    def test_cache_creates_parent_dirs(self, tmp_path):
        deep_path = str(tmp_path / "a" / "b" / "c" / "parsed_jd.json")
        original = _make_parsed_jd()
        cache_parsed_jd(original, deep_path)
        assert Path(deep_path).exists()

    def test_load_corrupted_cache_returns_none(self, tmp_path):
        cache_file = tmp_path / "parsed_jd.json"
        cache_file.write_text("NOT VALID JSON", encoding="utf-8")
        result = load_cached_jd(str(cache_file))
        assert result is None


# ---------------------------------------------------------------------------
# get_or_parse_jd (caching integration)
# ---------------------------------------------------------------------------

class TestGetOrParseJd:
    def _patched(self):
        return patch.multiple(
            "backend.app.core.jd_parser",
            _extract_with_gemini=MagicMock(return_value=MINIMAL_EXTRACTED),
            _generate_embedding_text_with_gemini=MagicMock(return_value="rich embedding"),
        )

    def test_first_call_hits_gemini(self, tmp_path):
        cache = str(tmp_path / "jd.json")
        mock_extract = MagicMock(return_value=MINIMAL_EXTRACTED)
        mock_embed = MagicMock(return_value="embedding")
        with patch.multiple(
            "backend.app.core.jd_parser",
            _extract_with_gemini=mock_extract,
            _generate_embedding_text_with_gemini=mock_embed,
        ):
            get_or_parse_jd(SAMPLE_JD, cache_path=cache)

        mock_extract.assert_called_once()

    def test_second_call_uses_cache(self, tmp_path):
        cache = str(tmp_path / "jd.json")
        mock_extract = MagicMock(return_value=MINIMAL_EXTRACTED)
        mock_embed = MagicMock(return_value="embedding")
        with patch.multiple(
            "backend.app.core.jd_parser",
            _extract_with_gemini=mock_extract,
            _generate_embedding_text_with_gemini=mock_embed,
        ):
            get_or_parse_jd(SAMPLE_JD, cache_path=cache)
            get_or_parse_jd(SAMPLE_JD, cache_path=cache)

        # Gemini should be called only once
        assert mock_extract.call_count == 1

    def test_force_refresh_bypasses_cache(self, tmp_path):
        cache = str(tmp_path / "jd.json")
        mock_extract = MagicMock(return_value=MINIMAL_EXTRACTED)
        mock_embed = MagicMock(return_value="embedding")
        with patch.multiple(
            "backend.app.core.jd_parser",
            _extract_with_gemini=mock_extract,
            _generate_embedding_text_with_gemini=mock_embed,
        ):
            get_or_parse_jd(SAMPLE_JD, cache_path=cache)
            get_or_parse_jd(SAMPLE_JD, cache_path=cache, force_refresh=True)

        assert mock_extract.call_count == 2

    def test_different_jd_invalidates_cache(self, tmp_path):
        cache = str(tmp_path / "jd.json")
        mock_extract = MagicMock(return_value=MINIMAL_EXTRACTED)
        mock_embed = MagicMock(return_value="embedding")
        with patch.multiple(
            "backend.app.core.jd_parser",
            _extract_with_gemini=mock_extract,
            _generate_embedding_text_with_gemini=mock_embed,
        ):
            get_or_parse_jd(SAMPLE_JD, cache_path=cache)
            get_or_parse_jd(SAMPLE_JD + " extra text", cache_path=cache)

        assert mock_extract.call_count == 2

    def test_accepts_txt_file_path(self, tmp_path):
        txt_file = tmp_path / "jd.txt"
        txt_file.write_text(SAMPLE_JD, encoding="utf-8")
        cache = str(tmp_path / "jd.json")

        mock_extract = MagicMock(return_value=MINIMAL_EXTRACTED)
        mock_embed = MagicMock(return_value="embedding")
        with patch.multiple(
            "backend.app.core.jd_parser",
            _extract_with_gemini=mock_extract,
            _generate_embedding_text_with_gemini=mock_embed,
        ):
            result = get_or_parse_jd(str(txt_file), cache_path=cache)

        assert isinstance(result, ParsedJD)


# ---------------------------------------------------------------------------
# Integration test (requires live GEMINI_API_KEY)
# ---------------------------------------------------------------------------

@pytest.mark.skipif(
    not os.getenv("GEMINI_API_KEY"),
    reason="GEMINI_API_KEY not set — skipping live integration test",
)
class TestIntegration:
    def test_parse_sample_jd_live(self, tmp_path):
        cache = str(tmp_path / "parsed_jd.json")
        result = get_or_parse_jd(SAMPLE_JD, cache_path=cache)

        assert isinstance(result, ParsedJD)
        assert result.role_title != ""
        assert len(result.required_skills) >= 1
        assert result.min_years_experience > 0
        assert len(result.jd_hash) == 32

        # Cache file should exist
        assert Path(cache).exists()

        # Second call should hit cache — Gemini not called again
        result2 = get_or_parse_jd(SAMPLE_JD, cache_path=cache)
        assert result2.jd_hash == result.jd_hash
