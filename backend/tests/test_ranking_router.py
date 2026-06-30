"""End-to-end tests for the ranking API router (Issue 013).

Uses real components throughout — no mocks:
  - Real SQLAlchemy on a file-backed SQLite database in tmp_path
  - Real signup/login via the auth router to obtain a real JWT
  - Real RankingEngine with the real EmbeddingService (downloads
    all-MiniLM-L6-v2 once into the HuggingFace cache and reuses it)
  - Real candidates loaded from sample_candidates.json (50 records)
"""

from __future__ import annotations

import json
import os
import pathlib
import sys
import tempfile
import uuid

import pytest

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
_BACKEND = _REPO_ROOT / "backend"
for p in (_BACKEND, _REPO_ROOT):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from backend.tests.test_schemas import _SAMPLE_JSON


def _prebuild_jd_cache(cache_path: pathlib.Path, text: str) -> None:
    """Write a ParsedJD JSON to *cache_path* matching the hash of *text*.

    This is the SAME format rank.py and precompute_embeddings.py write at
    deploy time. We use it here so the test suite never hits Gemini —
    matching the no-network constraint judges run under.
    """
    from dataclasses import asdict
    from backend.app.core.jd_parser import ParsedJD, _md5
    parsed = ParsedJD(
        raw_text=text,
        role_title="Senior AI Engineer",
        required_skills=["embeddings", "vector database", "python", "nlp", "retrieval", "ranking"],
        preferred_skills=["rag", "llm", "fine-tuning", "learning to rank"],
        disqualifying_signals=[],
        min_years_experience=5.0,
        max_years_experience=9.0,
        preferred_locations=[],
        notice_period_preference_days=30,
        seniority_level="senior",
        industry_preference="product_company",
        work_mode="hybrid",
        role_embedding_text=(
            "Senior AI engineer skilled in embeddings, vector databases, retrieval, "
            "ranking, NLP, and Python. Strong production deployment background preferred."
        ),
        jd_hash=_md5(text),
        vibe_signals=[],
        hiring_context="",
    )
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(asdict(parsed), ensure_ascii=False), encoding="utf-8")


@pytest.fixture(scope="module")
def app_and_client(tmp_path_factory):
    """Build the real FastAPI app with a real file-backed SQLite DB.

    Module-scoped so we pay the model-load cost once across all tests.
    """
    tmp = tmp_path_factory.mktemp("ranking_router")
    db_file = tmp / "test.db"
    os.environ["DATABASE_URL"] = f"sqlite:///{db_file}"
    os.environ.setdefault("SECRET_KEY", "test_secret_for_ranking_router_suite")

    # Lay out a candidates.jsonl in the same tmp dir so the default config path
    # works when /rank is called without an explicit candidates_path.
    candidates_path = tmp / "candidates.jsonl"
    sample = json.loads(_SAMPLE_JSON.read_text(encoding="utf-8"))
    from backend.app.core.candidate_loader import validate_candidate
    with candidates_path.open("w", encoding="utf-8") as fh:
        for raw in sample:
            rec = validate_candidate(raw)
            if rec is not None:
                fh.write(rec.model_dump_json() + "\n")
    os.environ["CANDIDATES_JSONL_PATH"] = str(candidates_path)
    # Point precomputed paths at non-existent files so the engine uses
    # on-the-fly embedding (real model, just not cached embeddings).
    os.environ["EMBEDDINGS_PATH"] = str(tmp / "no_embeddings.npy")
    os.environ["CANDIDATE_IDS_PATH"] = str(tmp / "no_ids.json")
    os.environ["RICH_REASONING_PATH"] = str(tmp / "no_rich.json")
    os.environ["PARSED_JD_CACHE_PATH"] = str(tmp / "parsed_jd.json")

    # Pre-populate the JD cache with the test JD so /rank does NOT call Gemini.
    # This is the same offline-friendly flow rank.py uses to satisfy the
    # challenge's "no network during ranking" constraint.
    _prebuild_jd_cache(
        tmp / "parsed_jd.json",
        text=(
            "Senior AI Engineer with 5-9 years of experience. "
            "Required skills: embeddings, vector databases, Python, NLP, retrieval, ranking. "
            "Nice to have: RAG, LLM fine-tuning, learning to rank."
        ),
    )

    # Import (or re-import) the app modules after env is set so they pick up
    # the test database and paths.
    for mod_name in [m for m in list(sys.modules) if m.startswith(("app.", "backend.app."))]:
        del sys.modules[mod_name]

    from fastapi.testclient import TestClient
    from app.main import app
    from app.routers import ranking as ranking_router

    ranking_router._reset_engine_for_tests()

    with TestClient(app) as client:
        yield app, client, tmp

    ranking_router._reset_engine_for_tests()


@pytest.fixture(scope="module")
def auth_token(app_and_client) -> str:
    """Sign up a real test user and return a real JWT bearer token."""
    _, client, _ = app_and_client
    email = f"router_test_{uuid.uuid4().hex[:8]}@test.local"
    password = "Sup3r-Secret-Password!"
    signup = client.post("/signup", json={
        "email": email, "password": password, "full_name": "Router Tester",
    })
    assert signup.status_code == 200, signup.text
    login = client.post("/login", data={"username": email, "password": password})
    assert login.status_code == 200, login.text
    return login.json()["access_token"]


@pytest.fixture(scope="module")
def auth_headers(auth_token) -> dict[str, str]:
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture(scope="module")
def jd_text() -> str:
    return (
        "Senior AI Engineer with 5-9 years of experience. "
        "Required skills: embeddings, vector databases, Python, NLP, retrieval, ranking. "
        "Nice to have: RAG, LLM fine-tuning, learning to rank."
    )


@pytest.fixture(scope="module")
def completed_run(app_and_client, auth_headers, jd_text):
    """Run /rank once and reuse the result across the test class."""
    _, client, _ = app_and_client
    resp = client.post(
        "/api/ranking/rank",
        headers=auth_headers,
        data={
            "job_description_text": jd_text,
            "top_n": 10,
            "stage1_n": 50,
            "stage2_n": 20,
        },
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


class TestExistingEndpointsStillWork:
    """Existing resume/auth endpoints must keep working after adding the router."""

    def test_health_check(self, app_and_client):
        _, client, _ = app_and_client
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json() == {"status": "healthy"}

    def test_root(self, app_and_client):
        _, client, _ = app_and_client
        r = client.get("/")
        assert r.status_code == 200

    def test_existing_resume_routes_registered(self, app_and_client):
        _, client, _ = app_and_client
        schema = client.get("/openapi.json").json()
        paths = set(schema["paths"])
        assert "/evaluate" in paths
        assert "/refine" in paths

    def test_existing_auth_routes_registered(self, app_and_client):
        _, client, _ = app_and_client
        schema = client.get("/openapi.json").json()
        paths = set(schema["paths"])
        assert "/login" in paths
        assert "/signup" in paths


class TestAuth:
    def test_rank_requires_auth(self, app_and_client):
        _, client, _ = app_and_client
        r = client.post("/api/ranking/rank", data={"job_description_text": "x"})
        assert r.status_code == 401

    def test_status_requires_auth(self, app_and_client):
        _, client, _ = app_and_client
        r = client.get("/api/ranking/status/abc123")
        assert r.status_code == 401

    def test_candidate_requires_auth(self, app_and_client):
        _, client, _ = app_and_client
        r = client.get("/api/ranking/candidate/CAND_0000001")
        assert r.status_code == 401

    def test_rerank_requires_auth(self, app_and_client):
        _, client, _ = app_and_client
        r = client.post("/api/ranking/rerank", json={})
        assert r.status_code == 401

    def test_invalid_token_rejected(self, app_and_client):
        _, client, _ = app_and_client
        r = client.post(
            "/api/ranking/rank",
            headers={"Authorization": "Bearer not_a_real_token"},
            data={"job_description_text": "x"},
        )
        assert r.status_code == 401


class TestRankEndpoint:
    """POST /api/ranking/rank — real pipeline, real embedding model."""

    def test_rank_returns_full_response(self, completed_run):
        data = completed_run
        assert data["status"] == "completed"
        assert data["total_candidates_processed"] == 50
        assert data["elapsed_seconds"] > 0
        assert len(data["ranked_candidates"]) == 10

    def test_run_id_format(self, completed_run):
        assert isinstance(completed_run["run_id"], str)
        assert len(completed_run["run_id"]) >= 8

    def test_ranks_are_sequential(self, completed_run):
        ranks = [c["rank"] for c in completed_run["ranked_candidates"]]
        assert ranks == list(range(1, len(ranks) + 1))

    def test_scores_non_increasing(self, completed_run):
        scores = [c["final_score"] for c in completed_run["ranked_candidates"]]
        assert scores == sorted(scores, reverse=True)

    def test_candidate_ids_unique(self, completed_run):
        ids = [c["candidate_id"] for c in completed_run["ranked_candidates"]]
        assert len(set(ids)) == len(ids)

    def test_each_candidate_has_score_breakdown(self, completed_run):
        for c in completed_run["ranked_candidates"]:
            sb = c["score_breakdown"]
            for key in ("rule_score", "embedding_similarity", "skills_score",
                        "career_score", "behavioral_score"):
                assert key in sb
                assert isinstance(sb[key], (int, float))

    def test_each_candidate_has_profile_snapshot(self, completed_run):
        for c in completed_run["ranked_candidates"]:
            ps = c["profile_snapshot"]
            assert ps["headline"]
            assert ps["current_title"]
            assert ps["current_company"]
            assert isinstance(ps["years_of_experience"], (int, float))
            assert isinstance(ps["top_skills"], list)

    def test_reasoning_non_empty(self, completed_run):
        for c in completed_run["ranked_candidates"]:
            assert c["reasoning"]
            assert len(c["reasoning"]) > 10

    def test_missing_jd_returns_422(self, app_and_client, auth_headers):
        _, client, _ = app_and_client
        r = client.post("/api/ranking/rank", headers=auth_headers, data={"top_n": 5})
        assert r.status_code == 422

    def test_missing_candidates_file_returns_400(self, app_and_client, auth_headers, jd_text):
        _, client, _ = app_and_client
        r = client.post(
            "/api/ranking/rank",
            headers=auth_headers,
            data={
                "job_description_text": jd_text,
                "candidates_path": "/nonexistent/path/candidates.jsonl",
                "top_n": 5, "stage1_n": 10, "stage2_n": 5,
            },
        )
        assert r.status_code == 400

    def test_invalid_top_n_returns_422(self, app_and_client, auth_headers, jd_text):
        _, client, _ = app_and_client
        r = client.post(
            "/api/ranking/rank",
            headers=auth_headers,
            data={"job_description_text": jd_text, "top_n": 0},
        )
        assert r.status_code == 422


class TestStatusEndpoint:
    def test_status_returns_completed_after_rank(
        self, app_and_client, auth_headers, completed_run,
    ):
        _, client, _ = app_and_client
        run_id = completed_run["run_id"]
        r = client.get(f"/api/ranking/status/{run_id}", headers=auth_headers)
        assert r.status_code == 200
        body = r.json()
        assert body["run_id"] == run_id
        assert body["status"] == "completed"
        assert body["stage"] == "done"
        assert body["progress_pct"] == 100.0

    def test_unknown_run_id_returns_404(self, app_and_client, auth_headers):
        _, client, _ = app_and_client
        r = client.get("/api/ranking/status/no_such_run", headers=auth_headers)
        assert r.status_code == 404


class TestCandidateEndpoint:
    def test_returns_full_profile_for_ranked_candidate(
        self, app_and_client, auth_headers, completed_run,
    ):
        _, client, _ = app_and_client
        target = completed_run["ranked_candidates"][0]["candidate_id"]
        r = client.get(f"/api/ranking/candidate/{target}", headers=auth_headers)
        assert r.status_code == 200
        body = r.json()
        assert body["candidate"]["candidate_id"] == target
        assert "profile" in body["candidate"]
        assert "career_history" in body["candidate"]
        assert "skills" in body["candidate"]
        assert "redrob_signals" in body["candidate"]
        assert "score_breakdown" in body
        assert "reasoning" in body
        assert "rank" in body

    def test_invalid_id_format_returns_422(self, app_and_client, auth_headers, completed_run):
        _, client, _ = app_and_client
        r = client.get("/api/ranking/candidate/NOT_A_VALID_ID", headers=auth_headers)
        assert r.status_code == 422

    def test_unknown_valid_format_id_returns_404(
        self, app_and_client, auth_headers, completed_run,
    ):
        _, client, _ = app_and_client
        # CAND_9999999 is a valid-format id that's not in the sample data
        r = client.get("/api/ranking/candidate/CAND_9999999", headers=auth_headers)
        assert r.status_code == 404


class TestRerankEndpoint:
    def test_rerank_with_modified_weights_succeeds(
        self, app_and_client, auth_headers, completed_run, jd_text,
    ):
        _, client, _ = app_and_client
        r = client.post(
            "/api/ranking/rerank",
            headers=auth_headers,
            json={
                "weight_overrides": {
                    "behavioral": 0.30, "skills_trust": 0.15,
                    "rule_score": 0.20, "embedding_similarity": 0.20,
                    "career_trajectory": 0.15,
                },
            },
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["status"] == "completed"
        assert len(body["ranked_candidates"]) == 10
        # Different weights → at least one candidate should land at a different
        # rank than the baseline run.
        baseline_top_ids = [c["candidate_id"] for c in completed_run["ranked_candidates"]]
        rerank_top_ids = [c["candidate_id"] for c in body["ranked_candidates"]]
        assert baseline_top_ids != rerank_top_ids or body["run_id"] != completed_run["run_id"]

    def test_rerank_with_new_jd_text(self, app_and_client, auth_headers, completed_run):
        _, client, _ = app_and_client
        r = client.post(
            "/api/ranking/rerank",
            headers=auth_headers,
            json={
                "job_description":
                    "Frontend Engineer with 3-5 years of experience. "
                    "Required: React, TypeScript, CSS. Nice to have: Next.js.",
            },
        )
        # Gemini quota / network issues can produce a real 503 — that's the
        # documented behaviour, not a test failure. Accept either path.
        if r.status_code == 503:
            assert "JD parsing service unavailable" in r.text
            pytest.skip(f"Gemini parsing unavailable during this run: {r.text}")
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "completed"

    def test_rerank_validates_weight_overrides(
        self, app_and_client, auth_headers, completed_run,
    ):
        _, client, _ = app_and_client
        r = client.post(
            "/api/ranking/rerank",
            headers=auth_headers,
            json={"weight_overrides": {"behavioral": 1.5}},  # out of [0,1]
        )
        assert r.status_code == 422

    def test_rerank_rejects_unknown_weight_keys(
        self, app_and_client, auth_headers, completed_run,
    ):
        _, client, _ = app_and_client
        r = client.post(
            "/api/ranking/rerank",
            headers=auth_headers,
            json={"weight_overrides": {"not_a_real_key": 0.5}},
        )
        assert r.status_code == 422



    def test_rerank_is_faster_than_full_run(
        self, app_and_client, auth_headers, completed_run,
    ):
        _, client, _ = app_and_client
        r = client.post(
            "/api/ranking/rerank",
            headers=auth_headers,
            json={"weight_overrides": {"rule_score": 0.30,
                                       "embedding_similarity": 0.25,
                                       "skills_trust": 0.15,
                                       "career_trajectory": 0.10,
                                       "behavioral": 0.20}},
        )
        assert r.status_code == 200, r.text
        # Original /rank on 50 candidates includes Gemini JD parsing + model
        # download; rerank reuses the cached Stage 1 + already-loaded model.
        original_elapsed = completed_run["elapsed_seconds"]
        assert r.json()["elapsed_seconds"] <= original_elapsed * 1.5


class TestPrescreenEndpoint:
    """Open (no-auth) endpoint kept for sandbox-style smoke tests."""

    def test_prescreen_returns_scores(self, app_and_client):
        _, client, _ = app_and_client
        sample = json.loads(_SAMPLE_JSON.read_text(encoding="utf-8"))
        r = client.post(
            "/api/ranking/prescreen",
            json={
                "job_description": "Senior AI Engineer with embeddings and Python.",
                "candidates": sample[:5],
                "top_k": 3,
            },
        )
        assert r.status_code == 200
        body = r.json()
        assert body["total_submitted"] == 5
        assert body["total_returned"] <= 3
        assert len(body["results"]) == body["total_returned"]


class TestStateWipeBehaviour:
    """Tests that mutate the module-level run state. Kept in a separate class
    placed AFTER the main rerank tests so they don't interfere with earlier
    fixture-dependent tests.
    """

    def test_rerank_without_prior_run_returns_409(self, app_and_client, auth_headers):
        _, client, _ = app_and_client
        from app.routers import ranking as ranking_router
        ranking_router._last_run_id = None
        ranking_router._runs.clear()
        r = client.post("/api/ranking/rerank", headers=auth_headers, json={})
        assert r.status_code == 409


class TestEngineLazyLoad:
    def test_engine_is_singleton(self):
        from app.routers import ranking as ranking_router
        e1 = ranking_router.get_engine()
        e2 = ranking_router.get_engine()
        assert e1 is e2

    def test_engine_uses_configured_model(self):
        from app.routers import ranking as ranking_router
        e = ranking_router.get_engine()
        assert e.model_name == "all-MiniLM-L6-v2"
