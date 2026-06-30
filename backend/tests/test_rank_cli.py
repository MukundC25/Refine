from __future__ import annotations

import csv
import json
import pathlib
import subprocess
import sys
import time
from dataclasses import asdict
from unittest.mock import patch

import pytest

import rank
from backend.app.core.candidate_loader import validate_candidate
from backend.app.core.jd_parser import ParsedJD
from backend.app.core.ranking_engine import RankingEngine
from backend.tests.test_ranking_engine import FakeEmbeddingService


_REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
_SAMPLE_JSON = (
    pathlib.Path(__file__).resolve().parents[3]
    / "[PUB] India_runs_data_and_ai_challenge"
    / "India_runs_data_and_ai_challenge"
    / "sample_candidates.json"
)


@pytest.fixture(scope="module")
def sample_raw() -> list[dict]:
    return json.loads(_SAMPLE_JSON.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def sample_records(sample_raw):
    return [r for r in (validate_candidate(d) for d in sample_raw) if r is not None]


@pytest.fixture(scope="module")
def stub_jd() -> ParsedJD:
    return ParsedJD(
        raw_text="Senior AI Engineer with 5-9 years experience in embeddings, NLP, Python.",
        role_title="Senior AI Engineer",
        required_skills=["embeddings", "vector database", "python", "nlp", "retrieval"],
        preferred_skills=["rag", "llm", "fine-tuning"],
        disqualifying_signals=[],
        min_years_experience=5.0,
        max_years_experience=9.0,
        preferred_locations=[],
        notice_period_preference_days=30,
        seniority_level="senior",
        industry_preference="product_company",
        work_mode="hybrid",
        role_embedding_text="Senior AI engineer with embeddings, NLP, retrieval, Python.",
        jd_hash="cli_test",
        vibe_signals=[],
        hiring_context="",
    )


@pytest.fixture
def setup_run(tmp_path, sample_records, stub_jd):
    """Lay out a complete temp workspace with candidates jsonl, JD file, and
    pre-cached parsed JD; return an argparse.Namespace ready for rank.run().
    """
    # Candidates jsonl
    candidates_path = tmp_path / "candidates.jsonl"
    with candidates_path.open("w", encoding="utf-8") as fh:
        for rec in sample_records:
            fh.write(rec.model_dump_json() + "\n")

    # JD source file (txt is fine; get_or_parse_jd treats it like text)
    jd_path = tmp_path / "job_description.txt"
    jd_path.write_text(stub_jd.raw_text, encoding="utf-8")

    # Pre-cache parsed JD so load_jd does not hit Gemini
    parsed_cache = tmp_path / "parsed_jd.json"
    # The cache must use the hash of the raw text used at runtime — write a
    # cached ParsedJD with the same hash get_or_parse_jd will compute.
    from backend.app.core.jd_parser import _md5
    cached = ParsedJD(**{**asdict(stub_jd), "jd_hash": _md5(stub_jd.raw_text),
                         "raw_text": stub_jd.raw_text})
    parsed_cache.write_text(
        json.dumps(asdict(cached), ensure_ascii=False), encoding="utf-8"
    )

    out_path = tmp_path / "submission.csv"

    args = rank.build_parser().parse_args([
        "--candidates", str(candidates_path),
        "--jd", str(jd_path),
        "--parsed-jd-cache", str(parsed_cache),
        "--embeddings", str(tmp_path / "missing.npy"),  # forces fallback
        "--rich-reasoning", str(tmp_path / "missing_rich.json"),
        "--out", str(out_path),
        "--top-n", "10",
        "--stage1-n", "50",
        "--stage2-n", "20",
    ])
    return args, tmp_path


def _patched_build_engine(args):
    """Replacement for rank.build_engine that injects FakeEmbeddingService."""
    rich_path = args.rich_reasoning if pathlib.Path(args.rich_reasoning).exists() else None
    return RankingEngine(
        embedding_service=FakeEmbeddingService(),
        rich_reasoning_path=rich_path,
    )


class TestBuildParser:
    def test_required_args(self):
        with pytest.raises(SystemExit):
            rank.build_parser().parse_args([])

    def test_defaults(self):
        args = rank.build_parser().parse_args([
            "--candidates", "x.jsonl", "--out", "y.csv",
        ])
        assert args.top_n == 100
        assert args.stage1_n == 5000
        assert args.stage2_n == 200
        assert args.log_level == "INFO"
        assert args.jd == "./job_description.docx"

    def test_overrides(self):
        args = rank.build_parser().parse_args([
            "--candidates", "x.jsonl", "--out", "y.csv",
            "--top-n", "5", "--stage1-n", "100", "--log-level", "DEBUG",
        ])
        assert args.top_n == 5
        assert args.stage1_n == 100
        assert args.log_level == "DEBUG"


class TestResolveJDPath:
    def test_existing_path_returned(self, tmp_path):
        p = tmp_path / "jd.docx"
        p.write_text("x")
        assert rank.resolve_jd_path(str(p)) == p

    def test_pdf_fallback_when_docx_missing(self, tmp_path):
        pdf = tmp_path / "jd.pdf"
        pdf.write_text("x")
        assert rank.resolve_jd_path(str(tmp_path / "jd.docx")) == pdf

    def test_returns_none_when_nothing_exists(self, tmp_path):
        assert rank.resolve_jd_path(str(tmp_path / "missing.docx")) is None

    def test_no_pdf_fallback_for_pdf_input(self, tmp_path):
        # Input is a .pdf; if missing we don't try anything else
        assert rank.resolve_jd_path(str(tmp_path / "jd.pdf")) is None


class TestValidateInputFiles:
    def test_raises_when_candidates_missing(self, tmp_path):
        args = rank.build_parser().parse_args([
            "--candidates", str(tmp_path / "missing.jsonl"),
            "--out", str(tmp_path / "out.csv"),
            "--jd", str(tmp_path / "jd.docx"),
        ])
        with pytest.raises(rank.MissingInputError, match="candidates file not found"):
            rank.validate_input_files(args)

    def test_raises_when_jd_missing(self, tmp_path):
        candidates = tmp_path / "candidates.jsonl"
        candidates.write_text("")
        args = rank.build_parser().parse_args([
            "--candidates", str(candidates),
            "--out", str(tmp_path / "out.csv"),
            "--jd", str(tmp_path / "missing.docx"),
        ])
        with pytest.raises(rank.MissingInputError, match="JD file not found"):
            rank.validate_input_files(args)

    def test_succeeds_with_all_files_present(self, tmp_path):
        candidates = tmp_path / "candidates.jsonl"
        candidates.write_text("")
        jd = tmp_path / "jd.docx"
        jd.write_text("")
        args = rank.build_parser().parse_args([
            "--candidates", str(candidates),
            "--out", str(tmp_path / "out.csv"),
            "--jd", str(jd),
        ])
        assert rank.validate_input_files(args) == jd


class TestWriteSubmissionCSV:
    def test_header_correct(self, tmp_path, sample_records, stub_jd):
        engine = RankingEngine(embedding_service=FakeEmbeddingService())
        ranked = engine.rank_records(sample_records[:5], stub_jd, top_n_final=5)
        out = tmp_path / "submission.csv"
        rank.write_submission_csv(ranked, str(out))
        with out.open(encoding="utf-8") as fh:
            reader = csv.reader(fh)
            assert next(reader) == rank.CSV_HEADER

    def test_row_count_matches_ranked(self, tmp_path, sample_records, stub_jd):
        engine = RankingEngine(embedding_service=FakeEmbeddingService())
        ranked = engine.rank_records(sample_records, stub_jd, top_n_final=10)
        out = tmp_path / "submission.csv"
        rank.write_submission_csv(ranked, str(out))
        with out.open(encoding="utf-8") as fh:
            rows = list(csv.reader(fh))
        assert len(rows) == len(ranked) + 1  # +1 for header

    def test_score_rounded_to_4_decimals(self, tmp_path, sample_records, stub_jd):
        engine = RankingEngine(embedding_service=FakeEmbeddingService())
        ranked = engine.rank_records(sample_records[:5], stub_jd, top_n_final=5)
        out = tmp_path / "submission.csv"
        rank.write_submission_csv(ranked, str(out))
        with out.open(encoding="utf-8") as fh:
            reader = csv.reader(fh)
            next(reader)
            for row in reader:
                score_str = row[2]
                assert len(score_str.split(".")[-1]) <= 4 if "." in score_str else True

    def test_utf8_encoding_preserves_warning_glyph(self, tmp_path, sample_records, stub_jd):
        engine = RankingEngine(embedding_service=FakeEmbeddingService())
        ranked = engine.rank_records(sample_records, stub_jd, top_n_final=20)
        out = tmp_path / "submission.csv"
        rank.write_submission_csv(ranked, str(out))
        text = out.read_text(encoding="utf-8")
        # Some reasoning strings include the ⚠ glyph for flagged candidates
        # but we only assert it survives if any flagged candidate is present
        flagged = any("⚠" in rc.reasoning for rc in ranked)
        if flagged:
            assert "⚠" in text

    def test_csv_quotes_commas_in_reasoning(self, tmp_path, sample_records, stub_jd):
        engine = RankingEngine(embedding_service=FakeEmbeddingService())
        ranked = engine.rank_records(sample_records[:3], stub_jd, top_n_final=3)
        # Inject a comma-laden reasoning to ensure csv.writer quotes it
        ranked[0].reasoning = "a, b, c; d, e"
        out = tmp_path / "submission.csv"
        rank.write_submission_csv(ranked, str(out))
        # Round-trip through csv.reader — quoting is invisible to the reader
        with out.open(encoding="utf-8") as fh:
            rows = list(csv.reader(fh))
        assert rows[1][3] == "a, b, c; d, e"


class TestValidateOutputCSV:
    def _write(self, path, rows):
        with open(path, "w", encoding="utf-8", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(rank.CSV_HEADER)
            for r in rows:
                w.writerow(r)

    def test_valid_csv_returns_no_errors(self, tmp_path):
        out = tmp_path / "ok.csv"
        rows = [
            ["CAND_0000001", 1, 99.5, "reasoning"],
            ["CAND_0000002", 2, 80.0, "reasoning"],
            ["CAND_0000003", 3, 50.0, "reasoning"],
        ]
        self._write(out, rows)
        assert rank.validate_output_csv(str(out), expected_rows=3) == []

    def test_wrong_header(self, tmp_path):
        out = tmp_path / "bad.csv"
        with out.open("w", encoding="utf-8", newline="") as fh:
            csv.writer(fh).writerow(["a", "b", "c", "d"])
        errors = rank.validate_output_csv(str(out), expected_rows=0)
        assert any("Header must be" in e for e in errors)

    def test_wrong_row_count(self, tmp_path):
        out = tmp_path / "few.csv"
        rows = [["CAND_0000001", 1, 99.0, "r"]]
        self._write(out, rows)
        errors = rank.validate_output_csv(str(out), expected_rows=5)
        assert any("Expected exactly 5 data rows" in e for e in errors)

    def test_invalid_candidate_id(self, tmp_path):
        out = tmp_path / "bad_id.csv"
        rows = [["BAD_ID", 1, 99.0, "r"]]
        self._write(out, rows)
        errors = rank.validate_output_csv(str(out), expected_rows=1)
        assert any("invalid candidate_id" in e for e in errors)

    def test_duplicate_candidate_id(self, tmp_path):
        out = tmp_path / "dup.csv"
        rows = [
            ["CAND_0000001", 1, 99.0, "r"],
            ["CAND_0000001", 2, 50.0, "r"],
        ]
        self._write(out, rows)
        errors = rank.validate_output_csv(str(out), expected_rows=2)
        assert any("duplicate candidate_id" in e for e in errors)

    def test_duplicate_rank(self, tmp_path):
        out = tmp_path / "dup_rank.csv"
        rows = [
            ["CAND_0000001", 1, 99.0, "r"],
            ["CAND_0000002", 1, 50.0, "r"],
        ]
        self._write(out, rows)
        errors = rank.validate_output_csv(str(out), expected_rows=2)
        assert any("duplicate rank" in e for e in errors)

    def test_score_non_increasing_violation(self, tmp_path):
        out = tmp_path / "asc.csv"
        rows = [
            ["CAND_0000001", 1, 50.0, "r"],
            ["CAND_0000002", 2, 99.0, "r"],  # higher score on lower rank
        ]
        self._write(out, rows)
        errors = rank.validate_output_csv(str(out), expected_rows=2)
        assert any("non-increasing" in e for e in errors)

    def test_tie_break_violation(self, tmp_path):
        out = tmp_path / "tie.csv"
        rows = [
            ["CAND_0000002", 1, 50.0, "r"],
            ["CAND_0000001", 2, 50.0, "r"],  # equal scores but cid desc
        ]
        self._write(out, rows)
        errors = rank.validate_output_csv(str(out), expected_rows=2)
        assert any("candidate_id ascending" in e for e in errors)

    def test_strict_mode_requires_100_rows(self, tmp_path):
        out = tmp_path / "few.csv"
        rows = [["CAND_0000001", 1, 99.0, "r"]]
        self._write(out, rows)
        errors = rank.validate_output_csv(str(out), expected_rows=1, strict=True)
        assert any("Expected exactly 100 data rows" in e for e in errors)


class TestMainExitCodes:
    def test_help_exits_zero(self, capsys):
        with pytest.raises(SystemExit) as exc:
            rank.main(["--help"])
        assert exc.value.code == 0

    def test_missing_candidates_exits_2(self, tmp_path, capsys):
        rc = rank.main([
            "--candidates", str(tmp_path / "missing.jsonl"),
            "--out", str(tmp_path / "out.csv"),
            "--jd", str(tmp_path / "missing.docx"),
        ])
        assert rc == rank.EXIT_MISSING_INPUT
        out = capsys.readouterr().out
        assert "candidates file not found" in out

    def test_missing_jd_exits_2(self, tmp_path, capsys):
        candidates = tmp_path / "candidates.jsonl"
        candidates.write_text("")
        rc = rank.main([
            "--candidates", str(candidates),
            "--out", str(tmp_path / "out.csv"),
            "--jd", str(tmp_path / "missing.docx"),
        ])
        assert rc == rank.EXIT_MISSING_INPUT


class TestEndToEnd:
    def test_full_pipeline_on_sample(self, setup_run, capsys):
        args, tmp_path = setup_run
        with patch.object(rank, "build_engine", _patched_build_engine):
            rc = rank.run(args)
        assert rc == rank.EXIT_OK, capsys.readouterr().out

        out = pathlib.Path(args.out)
        assert out.exists()
        with out.open(encoding="utf-8") as fh:
            rows = list(csv.reader(fh))
        # 1 header + 10 data rows
        assert rows[0] == rank.CSV_HEADER
        assert len(rows) == 11

    def test_progress_lines_printed(self, setup_run, capsys):
        args, _ = setup_run
        with patch.object(rank, "build_engine", _patched_build_engine):
            rc = rank.run(args)
        captured = capsys.readouterr().out
        # Spot-check the structured progress format
        assert "[rank.py]" in captured
        assert "Parsing job description" in captured
        assert "Stage" not in captured or "Pipeline complete" in captured
        assert "Validation passed" in captured

    def test_completes_under_10_seconds(self, setup_run):
        args, _ = setup_run
        start = time.perf_counter()
        with patch.object(rank, "build_engine", _patched_build_engine):
            rc = rank.run(args)
        elapsed = time.perf_counter() - start
        assert rc == rank.EXIT_OK
        assert elapsed < 10.0, f"sample run took {elapsed:.1f}s, expected <10s"

    def test_output_csv_round_trip_valid(self, setup_run, capsys):
        args, _ = setup_run
        with patch.object(rank, "build_engine", _patched_build_engine):
            rank.run(args)
        # Re-validate from scratch (no in-memory state)
        errors = rank.validate_output_csv(args.out, expected_rows=10)
        assert errors == []

    def test_ranks_unique_and_sequential(self, setup_run):
        args, _ = setup_run
        with patch.object(rank, "build_engine", _patched_build_engine):
            rank.run(args)
        with open(args.out, encoding="utf-8") as fh:
            reader = csv.reader(fh)
            next(reader)
            ranks = [int(row[1]) for row in reader]
        assert ranks == list(range(1, len(ranks) + 1))

    def test_real_build_engine_warns_on_missing_embeddings(self, setup_run, capsys):
        args, _ = setup_run
        # Use the real build_engine — but RankingEngine() with no path falls
        # back to a default EmbeddingService which would try to load the model.
        # We only need to verify the warning is printed; we don't actually run
        # the pipeline. Mock RankingEngine to a sentinel.
        class _Stub:
            def __init__(self, *a, **kw):
                self.kw = kw
        with patch("backend.app.core.ranking_engine.RankingEngine", _Stub):
            engine = rank.build_engine(args)
        captured = capsys.readouterr().out
        assert "embeddings not found" in captured.lower()


class TestModuleNotFoundHandling:
    def test_missing_ml_dep_exits_2_with_clear_message(self, setup_run, capsys):
        args, _ = setup_run

        class _BrokenEngine:
            def __init__(self, *a, **kw):
                pass
            def run(self, *a, **kw):
                raise ModuleNotFoundError(name="sentence_transformers")

        with patch.object(rank, "build_engine", lambda a: _BrokenEngine()):
            rc = rank.run(args)
        assert rc == rank.EXIT_MISSING_INPUT
        out = capsys.readouterr().out
        assert "sentence_transformers" in out
        assert "precompute_embeddings" in out


class TestImportability:
    def test_module_imports_without_side_effects(self):
        # Importing rank must not execute the pipeline. Verify by importing
        # again in a subprocess and inspecting exit code + output.
        result = subprocess.run(
            [sys.executable, "-c", "import rank; print('imported ok')"],
            capture_output=True, text=True, cwd=str(_REPO_ROOT),
        )
        assert result.returncode == 0
        assert "imported ok" in result.stdout
        # No [rank.py] progress lines should have leaked out
        assert "[rank.py]" not in result.stdout
