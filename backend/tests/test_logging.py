import json
import logging
import tempfile
import pathlib
from logging.handlers import RotatingFileHandler

import pytest
from httpx import AsyncClient, ASGITransport

from app.core.logging_config import configure_logging
from app.main import app
from app.core.ranking_engine import RankingEngine
from app.core.candidate_loader import validate_candidate, CandidateRecord
from app.core.jd_parser import ParsedJD

_SAMPLE_JSON = (
    pathlib.Path(__file__).resolve().parents[2]
    / "[PUB] India_runs_data_and_ai_challenge"
    / "[PUB] India_runs_data_and_ai_challenge"
    / "India_runs_data_and_ai_challenge"
    / "sample_candidates.json"
)

@pytest.fixture(scope="module")
def sample_raw() -> list[dict]:
    return json.loads(_SAMPLE_JSON.read_text(encoding="utf-8"))

@pytest.fixture(scope="module")
def sample_records(sample_raw) -> list[CandidateRecord]:
    return [r for r in (validate_candidate(d) for d in sample_raw) if r is not None]

@pytest.fixture(scope="module")
def senior_ai_jd() -> ParsedJD:
    return ParsedJD(
        raw_text="Senior AI Engineer with 5-9 years experience in embeddings, retrieval, NLP.",
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
        role_embedding_text="Senior AI engineer with embeddings, retrieval, NLP, Python.",
        jd_hash="test010",
        vibe_signals=[],
        hiring_context="",
    )

@pytest.fixture(autouse=True)
def setup_logging_for_test(tmp_path):
    log_file = tmp_path / "test_audit.log"
    configure_logging(log_file=str(log_file), level="INFO")
    yield log_file


def test_logging_configuration(setup_logging_for_test):
    log_file = setup_logging_for_test
    root = logging.getLogger()
    
    file_handlers = [h for h in root.handlers if isinstance(h, RotatingFileHandler)]
    assert len(file_handlers) >= 1
    file_handler = file_handlers[0]
    
    assert file_handler.maxBytes == 50 * 1024 * 1024
    assert file_handler.backupCount == 5
    assert file_handler.baseFilename == str(log_file.resolve())


@pytest.mark.asyncio
async def test_api_middleware_logging(setup_logging_for_test):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        await ac.get("/health")
        
    with open(setup_logging_for_test, "r", encoding="utf-8") as f:
        lines = f.readlines()
        
    api_logs = [json.loads(line) for line in lines if json.loads(line).get("event") == "api_request"]
    assert len(api_logs) >= 1
    log_entry = api_logs[-1]
    assert log_entry["endpoint"] == "GET /health"
    assert log_entry["status_code"] == 200
    assert "elapsed_ms" in log_entry
    assert log_entry["level"] == "info"


def test_pipeline_logging(setup_logging_for_test, sample_records, senior_ai_jd):
    engine = RankingEngine()
    
    with tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8") as tf:
        for r in sample_records:
            tf.write(r.model_dump_json() + "\n")
        tf_name = tf.name
        
    engine.run(candidates_path=tf_name, jd=senior_ai_jd, top_n_stage1=5, top_n_stage2=2, top_n_final=1)
    
    with open(setup_logging_for_test, "r", encoding="utf-8") as f:
        lines = f.readlines()
        
    logs = [json.loads(line) for line in lines]
    
    started = [l for l in logs if l.get("event") == "ranking_started"]
    assert len(started) == 1
    run_id = started[0]["run_id"]
    
    stage1 = [l for l in logs if l.get("event") == "stage1_complete"]
    assert len(stage1) == 1
    assert stage1[0]["run_id"] == run_id
    assert "candidates_in" in stage1[0]
    assert "candidates_out" in stage1[0]
    assert "honeypots_excluded" in stage1[0]
    assert "elapsed_s" in stage1[0]
    
    stage2 = [l for l in logs if l.get("event") == "stage2_complete"]
    assert len(stage2) == 1
    assert stage2[0]["run_id"] == run_id
    assert "candidates_in" in stage2[0]
    assert "candidates_out" in stage2[0]
    assert "elapsed_s" in stage2[0]

    stage3 = [l for l in logs if l.get("event") == "stage3_complete"]
    assert len(stage3) == 1
    assert stage3[0]["run_id"] == run_id
    assert "candidates_in" in stage3[0]
    assert "candidates_out" in stage3[0]
    assert "elapsed_s" in stage3[0]

    completed = [l for l in logs if l.get("event") == "ranking_complete"]
    assert len(completed) == 1
    assert completed[0]["run_id"] == run_id
    assert "top1_candidate" in completed[0]
    assert "top1_score" in completed[0]
    assert "total_elapsed_s" in completed[0]
    
    honeypots = [l for l in logs if l.get("event") == "honeypot_flagged"]
    if honeypots:
        h_log = honeypots[0]
        assert h_log["run_id"] == run_id
        assert "candidate_id" in h_log
        assert "flags" in h_log
        assert "penalty" in h_log
        assert h_log["level"] == "warning"
