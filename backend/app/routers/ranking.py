"""Ranking API router — bulk candidate ranking endpoints.

Exposes the 3-stage hybrid pipeline (Issues 004-011) over HTTP for the
recruiter dashboard and sandbox demo. All endpoints require JWT auth via
the same get_current_user dependency used by the existing resume routes.

Endpoints (prefix /api/ranking):
  POST /rank              full pipeline run on candidates.jsonl
  GET  /status/{run_id}   poll a previous run's status
  GET  /candidate/{cid}   full profile + score breakdown from the last run
  POST /rerank            stage 2+3 only, reusing stage 1 from the last run
  POST /prescreen         stage 1 rule pre-score on an inline batch (no auth)
                          retained for quick dev tests and pre-Gemini smoke runs
"""

from __future__ import annotations

import logging
import re
import shutil
import tempfile
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
    status,
)
from pydantic import BaseModel, Field

from app import config
from app.limiter import limiter
from app.models.schemas import (
    ProfileSnapshot,
    RankedCandidateResponse,
    RankingResponse,
    RankingStatusResponse,
    ReRankRequest,
    RuleScoreSchema,
    ScoreBreakdown,
)
from app.routers.auth import get_current_user

from app.core.candidate_loader import (
    CandidateRecord,
    load_all_candidates,
    validate_candidate,
)
from app.core.jd_parser import (
    ParsedJD,
    get_or_parse_jd,
    parse_jd_from_text,
)
from app.core.ranking_engine import (
    RankedCandidate,
    RankingEngine,
    STAGE_WEIGHTS,
    stage1_from_records,
    stage2_semantic_rerank,
    stage3_behavioral_boost,
)
from app.core.rule_scorer import (
    _DEFAULT_PREFERRED_SKILLS,
    _DEFAULT_REQUIRED_SKILLS,
    batch_score,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ranking", tags=["ranking"])

ALLOWED_JD_SUFFIXES = {".docx", ".pdf"}  # .txt excluded per Issue 016 spec
MAX_JD_LENGTH = 50_000          # ~10 K words — well above any real JD
MAX_UPLOAD_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB


@dataclass
class _RunState:
    """In-memory state for one ranking run."""
    run_id: str
    status: str = "running"          # running | completed | failed
    stage: str = "stage_1"            # stage_1 | stage_2 | stage_3 | done
    progress_pct: float = 0.0
    message: str = ""
    started_at: float = field(default_factory=time.perf_counter)
    elapsed_seconds: float = 0.0
    honeypots_excluded: int = 0
    total_candidates_processed: int = 0
    jd: ParsedJD | None = None
    stage1_cache: list[tuple] | None = None
    stage2_cache: list[tuple] | None = None
    ranked: list[RankedCandidate] = field(default_factory=list)


# Module-level state. Reset on app restart. For multi-worker production, this
# would move to Redis — but for the single-worker sandbox demo it is enough.
_runs: dict[str, _RunState] = {}
_last_run_id: str | None = None
_engine: RankingEngine | None = None


def get_engine() -> RankingEngine:
    """Lazy-initialise the shared RankingEngine.

    Loading is deferred until the first ranking call so app startup stays fast.
    Pre-computed embeddings and rich-reasoning caches are picked up from
    config paths if they exist on disk.
    """
    global _engine
    if _engine is not None:
        return _engine

    embeddings_path = config.EMBEDDINGS_PATH if Path(config.EMBEDDINGS_PATH).exists() else None
    rich_path = config.RICH_REASONING_PATH if Path(config.RICH_REASONING_PATH).exists() else None
    ids_path = config.CANDIDATE_IDS_PATH if (
        embeddings_path and Path(config.CANDIDATE_IDS_PATH).exists()
    ) else None

    _engine = RankingEngine(
        embeddings_path=embeddings_path,
        ids_path=ids_path,
        model_name=config.EMBEDDING_MODEL_NAME,
        rich_reasoning_path=rich_path,
    )
    logger.info(
        "RankingEngine initialised: embeddings=%s ids=%s rich_reasoning=%s model=%s",
        embeddings_path, ids_path, rich_path, config.EMBEDDING_MODEL_NAME,
    )
    return _engine


def _reset_engine_for_tests() -> None:
    """Clear the cached engine and run state — used between test functions."""
    global _engine, _last_run_id
    _engine = None
    _last_run_id = None
    _runs.clear()


async def _parse_jd_from_upload(file: UploadFile) -> ParsedJD:
    """Persist the upload to a temp file and run get_or_parse_jd (cached).

    get_or_parse_jd writes results to PARSED_JD_CACHE_PATH and skips Gemini
    when the content hash matches — the same offline-friendly flow rank.py uses.
    """
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_JD_SUFFIXES:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported JD file type: {suffix}. Use .docx or .pdf.",
        )

    content = await file.read()
    if len(content) > MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large (max {MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)}MB).",
        )

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        try:
            return get_or_parse_jd(tmp_path, cache_path=config.PARSED_JD_CACHE_PATH)
        except Exception as exc:
            logger.warning("Gemini JD parse from file failed (%s); using keyword fallback.", exc)
            text = Path(tmp_path).read_text(encoding="utf-8", errors="replace")
            return _jd_from_text_no_gemini(text)
    finally:
        Path(tmp_path).unlink(missing_ok=True)


async def _load_jd(
    job_description_text: str | None,
    job_description_file: UploadFile | None,
) -> ParsedJD:
    if job_description_file is not None and job_description_file.filename:
        return await _parse_jd_from_upload(job_description_file)
    if job_description_text and job_description_text.strip():
        text = job_description_text.strip()
        if len(text) > MAX_JD_LENGTH:
            raise HTTPException(
                status_code=422,
                detail=f"Job description too long: {len(text)} chars (max {MAX_JD_LENGTH}).",
            )
        try:
            return get_or_parse_jd(text, cache_path=config.PARSED_JD_CACHE_PATH)
        except Exception as exc:
            # Gemini quota exhausted or network unavailable — fall back to the
            # keyword-based parser so ranking still works without a Gemini key.
            logger.warning("Gemini JD parse failed (%s); using keyword fallback.", exc)
            return _jd_from_text_no_gemini(text)
    raise HTTPException(
        status_code=422,
        detail="Either job_description_text or job_description_file is required.",
    )


def _load_candidates(candidates_path: str) -> list[CandidateRecord]:
    path = Path(candidates_path)
    if not path.exists():
        raise HTTPException(
            status_code=400,
            detail=f"Candidates file not found: {candidates_path}",
        )
    try:
        return load_all_candidates(str(path))
    except Exception as exc:
        logger.exception("Failed to load candidates from %s", candidates_path)
        raise HTTPException(
            status_code=400,
            detail=f"Failed to load candidates: {exc}",
        )


def _validate_weights(overrides: dict[str, float] | None) -> dict[str, float] | None:
    if overrides is None:
        return None
    allowed = set(STAGE_WEIGHTS)
    for key, val in overrides.items():
        if key not in allowed:
            raise HTTPException(
                status_code=422,
                detail=f"Unknown weight key {key!r}. Allowed: {sorted(allowed)}.",
            )
        if not isinstance(val, (int, float)) or not 0.0 <= val <= 1.0:
            raise HTTPException(
                status_code=422,
                detail=f"Weight {key!r} must be a number in [0, 1]; got {val!r}.",
            )
    merged = {**STAGE_WEIGHTS, **overrides}
    total = sum(merged.values())
    if abs(total - 1.0) > 0.01:
        raise HTTPException(
            status_code=422,
            detail=f"Weight overrides must sum (with defaults) to 1.0; got {total:.4f}.",
        )
    return merged


def _top_skills(candidate: CandidateRecord, n: int = 5) -> list[str]:
    """Return the top N skill names by endorsement count."""
    return [
        s.name for s in sorted(
            candidate.skills, key=lambda x: x.endorsements, reverse=True,
        )[:n]
    ]


def _to_response(rc: RankedCandidate) -> RankedCandidateResponse:
    return RankedCandidateResponse(
        rank=rc.rank,
        candidate_id=rc.candidate.candidate_id,
        final_score=rc.final_score,
        reasoning=rc.reasoning,
        score_breakdown=ScoreBreakdown(
            rule_score=rc.rule_score.total,
            embedding_similarity=rc.embedding_similarity,
            skills_score=rc.skills_score.total,
            career_score=rc.career_score.total,
            behavioral_score=rc.behavioral_score.total,
        ),
        profile_snapshot=ProfileSnapshot(
            headline=rc.candidate.profile.headline,
            current_title=rc.candidate.profile.current_title,
            current_company=rc.candidate.profile.current_company,
            years_of_experience=rc.candidate.profile.years_of_experience,
            top_skills=_top_skills(rc.candidate),
        ),
    )


def _execute_pipeline(
    state: _RunState,
    candidates: list[CandidateRecord],
    jd: ParsedJD,
    top_n_stage1: int,
    top_n_stage2: int,
    top_n_final: int,
    weights: dict[str, float] | None = None,
) -> list[RankedCandidate]:
    """Run all 3 stages, populating *state* incrementally so /status can observe."""
    engine = get_engine()
    effective_weights = weights or engine.weights

    state.jd = jd
    state.stage = "stage_1"
    state.message = f"Stage 1: scoring {len(candidates)} candidates"
    stage1 = stage1_from_records(candidates, jd, top_n=top_n_stage1)
    state.stage1_cache = stage1
    state.honeypots_excluded = sum(1 for c in candidates if c.candidate_id not in {
        rec.candidate_id for rec, _, _ in stage1
    })
    state.progress_pct = 33.0

    state.stage = "stage_2"
    state.message = f"Stage 2: semantic rerank on {len(stage1)} survivors"
    jd_embedding = engine._jd_embedding(jd)
    stage2 = stage2_semantic_rerank(
        stage1, jd, jd_embedding, engine.embedding_service,
        embeddings_matrix=engine.embeddings_matrix,
        candidate_id_index=engine.candidate_id_index,
        top_n=top_n_stage2,
        weights=effective_weights,
    )
    state.stage2_cache = stage2
    state.progress_pct = 66.0

    state.stage = "stage_3"
    state.message = f"Stage 3: behavioural boost on {len(stage2)} survivors"
    ranked = stage3_behavioral_boost(
        stage2, jd, top_n=top_n_final, weights=effective_weights,
        rich_reasoning_cache=engine.rich_reasoning_cache,
    )
    state.stage = "done"
    state.progress_pct = 100.0
    state.message = f"Completed: top {len(ranked)} of {len(candidates)} candidates"
    return ranked


@router.post("/rank", response_model=RankingResponse)
@limiter.limit("2/minute")
async def rank_candidates(
    request: Request,
    job_description_text: Optional[str] = Form(None),
    job_description_file: Optional[UploadFile] = File(None),
    candidates_path: Optional[str] = Form(None),
    top_n: int = Form(100),
    stage1_n: int = Form(5000),
    stage2_n: int = Form(200),
    current_user=Depends(get_current_user),
) -> RankingResponse:
    """Full 3-stage pipeline. Returns the top-N ranked candidates synchronously."""
    global _last_run_id

    if top_n <= 0:
        raise HTTPException(status_code=422, detail="top_n must be a positive integer.")
    cand_path = candidates_path or config.CANDIDATES_JSONL_PATH

    run_id = uuid.uuid4().hex[:12]
    state = _RunState(run_id=run_id)
    _runs[run_id] = state

    try:
        try:
            jd = await _load_jd(job_description_text, job_description_file)
        except HTTPException:
            raise
        candidates = _load_candidates(cand_path)
        state.total_candidates_processed = len(candidates)

        ranked = _execute_pipeline(
            state, candidates, jd,
            top_n_stage1=stage1_n, top_n_stage2=stage2_n, top_n_final=top_n,
        )
        state.ranked = ranked
        state.status = "completed"
        # Only promote to _last_run_id after a successful run so failed runs
        # cannot shadow a previously-good result for /candidate or /rerank.
        _last_run_id = run_id
    except HTTPException:
        state.status = "failed"
        state.stage = "done"
        state.message = "input validation failed"
        raise
    except Exception as exc:
        logger.exception("Ranking run %s failed", run_id)
        state.status = "failed"
        state.stage = "done"
        state.message = f"error: {exc}"
        raise HTTPException(status_code=500, detail=f"Ranking failed: {exc}")
    finally:
        state.elapsed_seconds = time.perf_counter() - state.started_at

    return RankingResponse(
        run_id=run_id,
        status=state.status,
        elapsed_seconds=round(state.elapsed_seconds, 3),
        total_candidates_processed=state.total_candidates_processed,
        honeypots_excluded=state.honeypots_excluded,
        ranked_candidates=[_to_response(rc) for rc in ranked],
    )


@router.get("/status/{run_id}", response_model=RankingStatusResponse)
@limiter.limit("60/minute")
async def get_ranking_status(
    request: Request,
    run_id: str,
    current_user=Depends(get_current_user),
) -> RankingStatusResponse:
    state = _runs.get(run_id)
    if state is None:
        raise HTTPException(status_code=404, detail=f"Unknown run_id: {run_id}")
    return RankingStatusResponse(
        run_id=state.run_id,
        status=state.status,
        stage=state.stage,
        progress_pct=state.progress_pct,
        elapsed_seconds=round(state.elapsed_seconds, 3),
        message=state.message,
    )


@router.get("/candidate/{candidate_id}")
@limiter.limit("60/minute")
async def get_candidate_detail(
    request: Request,
    candidate_id: str,
    current_user=Depends(get_current_user),
) -> dict[str, Any]:
    """Return the full CandidateRecord + score breakdown from the most recent run."""
    if not re.match(r"^CAND_[0-9]{7}$", candidate_id):
        raise HTTPException(
            status_code=422,
            detail=f"Invalid candidate_id format: {candidate_id!r}. Expected CAND_NNNNNNN.",
        )
    if _last_run_id is None:
        raise HTTPException(
            status_code=404,
            detail="No ranking run available. Call POST /api/ranking/rank first.",
        )
    state = _runs[_last_run_id]
    match = next((rc for rc in state.ranked if rc.candidate.candidate_id == candidate_id), None)
    if match is None:
        raise HTTPException(
            status_code=404,
            detail=f"Candidate {candidate_id} not found in run {_last_run_id}.",
        )
    return {
        "candidate": match.candidate.model_dump(mode="json"),
        "rank": match.rank,
        "final_score": match.final_score,
        "reasoning": match.reasoning,
        "score_breakdown": ScoreBreakdown(
            rule_score=match.rule_score.total,
            embedding_similarity=match.embedding_similarity,
            skills_score=match.skills_score.total,
            career_score=match.career_score.total,
            behavioral_score=match.behavioral_score.total,
        ).model_dump(),
        "honeypot_flags": list(match.honeypot_result.flags),
    }


@router.post("/rerank", response_model=RankingResponse)
@limiter.limit("10/minute")
async def rerank_candidates(
    request: Request,
    body: ReRankRequest,
    current_user=Depends(get_current_user),
) -> RankingResponse:
    """Re-run Stage 2 + Stage 3 using cached Stage 1 survivors from the last run.

    Suitable for sliding score weights or trying alternate JD wordings without
    paying the Stage 1 scanning cost again.
    """
    global _last_run_id
    # Validate weights FIRST so callers get a 422 even when no prior run exists.
    weights = _validate_weights(body.weight_overrides)

    if _last_run_id is None:
        raise HTTPException(
            status_code=409,
            detail="No prior ranking run to rerank. Call POST /api/ranking/rank first.",
        )
    prior = _runs[_last_run_id]
    if prior.stage1_cache is None or prior.jd is None:
        raise HTTPException(
            status_code=409,
            detail="Prior run has no cached Stage 1 results (likely failed mid-run).",
        )

    if body.job_description and body.job_description.strip():
        try:
            jd = get_or_parse_jd(
                body.job_description, cache_path=config.PARSED_JD_CACHE_PATH,
            )
        except Exception as exc:
            # Gemini quota/network — fall back to keyword parser
            logger.warning("Gemini parse failed during rerank (%s); keyword fallback.", exc)
            jd = _jd_from_text_no_gemini(body.job_description)
    else:
        jd = prior.jd

    run_id = uuid.uuid4().hex[:12]
    state = _RunState(run_id=run_id, total_candidates_processed=prior.total_candidates_processed,
                      honeypots_excluded=prior.honeypots_excluded, jd=jd)
    _runs[run_id] = state

    engine = get_engine()
    try:
        state.stage1_cache = prior.stage1_cache
        state.stage = "stage_2"
        state.message = "Stage 2: rerank from cached Stage 1"
        jd_embedding = engine._jd_embedding(jd)
        stage2 = stage2_semantic_rerank(
            prior.stage1_cache, jd, jd_embedding, engine.embedding_service,
            embeddings_matrix=engine.embeddings_matrix,
            candidate_id_index=engine.candidate_id_index,
            top_n=len(prior.stage2_cache or prior.stage1_cache),
            weights=weights or engine.weights,
        )
        state.stage2_cache = stage2
        state.progress_pct = 66.0

        state.stage = "stage_3"
        state.message = "Stage 3: behavioural boost"
        top_n = len(prior.ranked) or 100
        ranked = stage3_behavioral_boost(
            stage2, jd, top_n=top_n, weights=weights or engine.weights,
            rich_reasoning_cache=engine.rich_reasoning_cache,
        )
        state.ranked = ranked
        state.stage = "done"
        state.status = "completed"
        state.progress_pct = 100.0
        state.message = f"Rerank complete: top {len(ranked)}"
    except Exception as exc:
        logger.exception("Rerank %s failed", run_id)
        state.status = "failed"
        raise HTTPException(status_code=500, detail=f"Rerank failed: {exc}")
    finally:
        state.elapsed_seconds = time.perf_counter() - state.started_at

    # Mark as the new "last run" so subsequent /candidate and /rerank target it
    _last_run_id = run_id

    return RankingResponse(
        run_id=run_id,
        status="completed",
        elapsed_seconds=round(state.elapsed_seconds, 3),
        total_candidates_processed=state.total_candidates_processed,
        honeypots_excluded=state.honeypots_excluded,
        ranked_candidates=[_to_response(rc) for rc in ranked],
    )


class PrescreenRequest(BaseModel):
    job_description: str = Field(..., min_length=20)
    candidates: list[dict[str, Any]] = Field(..., min_length=1)
    top_k: int = Field(default=100, ge=1, le=10_000)


class PrescreenResponse(BaseModel):
    total_submitted: int
    total_valid: int
    total_returned: int
    results: list[RuleScoreSchema]


@router.post("/prescreen", response_model=PrescreenResponse, summary="Stage 1 rule pre-screen")
async def prescreen_candidates(request: PrescreenRequest) -> PrescreenResponse:
    """Stage 1 rule pre-score on an inline candidate batch.

    No auth required (kept open for sandbox-style smoke tests). Uses a
    keyword-extracted ParsedJD so no GEMINI_API_KEY is required.
    """
    valid = [r for raw in request.candidates if (r := validate_candidate(raw)) is not None]
    if not valid:
        raise HTTPException(status_code=422, detail="No valid candidate records found.")
    jd = _jd_from_text_no_gemini(request.job_description)
    scores = sorted(batch_score(valid, jd), key=lambda s: s.total, reverse=True)
    top = scores[: request.top_k]
    return PrescreenResponse(
        total_submitted=len(request.candidates),
        total_valid=len(valid),
        total_returned=len(top),
        results=[
            RuleScoreSchema(
                candidate_id=s.candidate_id,
                experience_score=s.experience_score,
                title_score=s.title_score,
                skills_score=s.skills_score,
                industry_score=s.industry_score,
                disqualifier_penalty=s.disqualifier_penalty,
                total=s.total,
            )
            for s in top
        ],
    )


def _jd_from_text_no_gemini(text: str) -> ParsedJD:
    """Build a ParsedJD from raw text without calling Gemini (used by /prescreen)."""
    text_lower = text.lower()
    yoe_min, yoe_max = 5.0, 9.0
    if m := re.search(r"(\d+)\s*[-–to]+\s*(\d+)\s*years?", text_lower):
        yoe_min, yoe_max = float(m.group(1)), float(m.group(2))
    elif m := re.search(r"(\d+)\+?\s*years?", text_lower):
        yoe_min = float(m.group(1))
        yoe_max = yoe_min + 4

    # Extract required skills by matching known technical skill keywords in the text.
    # This gives each JD a distinct skill set even without Gemini.
    all_skills = list(_DEFAULT_REQUIRED_SKILLS) + list(_DEFAULT_PREFERRED_SKILLS)
    found_required = [s for s in all_skills if s.lower() in text_lower]
    required = found_required if len(found_required) >= 3 else list(_DEFAULT_REQUIRED_SKILLS)

    # Extract preferred skills as the next tier of keywords
    found_preferred = [s for s in _DEFAULT_PREFERRED_SKILLS if s.lower() in text_lower]

    # Extract role title — first line that looks like a job title
    role_title = ""
    for line in text.splitlines():
        line = line.strip()
        if 3 < len(line) < 80 and not line.startswith(("#", "-", "*", "/")):
            role_title = line
            break

    import hashlib
    jd_hash = hashlib.md5(text.encode("utf-8")).hexdigest()

    return ParsedJD(
        raw_text=text,
        role_title=role_title,
        required_skills=required,
        preferred_skills=found_preferred or list(_DEFAULT_PREFERRED_SKILLS),
        disqualifying_signals=[],
        min_years_experience=yoe_min,
        max_years_experience=yoe_max,
        preferred_locations=[],
        notice_period_preference_days=30,
        seniority_level="senior",
        industry_preference="any" if "consulting" in text_lower else "product_company",
        work_mode="hybrid",
        role_embedding_text=text[:2000],  # first 2000 chars as embedding text
        jd_hash=jd_hash,
        vibe_signals=[],
        hiring_context="",
    )
