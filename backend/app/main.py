import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

from app import config
from app.limiter import limiter
from app.routers import ranking
from app.core.logging_config import configure_logging, log

# Initialize logging globally
configure_logging(level=config.LOG_LEVEL)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Create database tables
    from app.database import engine
    from app.models import user
    print("Creating database tables...")
    user.Base.metadata.create_all(bind=engine)
    print("Database tables created successfully")
    yield
    # Shutdown: cleanup if needed
    print("Shutting down...")


app = FastAPI(
    title="Refine API",
    description="Backend for the Refine resume optimization app",
    version="1.0.0",
    lifespan=lifespan,
)

# ── SlowAPI rate limiting (Issue 016) ─────────────────────────────────────── #
app.state.limiter = limiter


def _custom_rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """Return exactly {"error": "Rate limit exceeded"} as required by Issue 016 spec.

    The built-in SlowAPI handler appends exc.detail (e.g. "2 per 1 minute") which
    does not match the required response shape. We keep the Retry-After / X-RateLimit
    headers so clients can implement exponential back-off.
    """
    response = JSONResponse({"error": "Rate limit exceeded"}, status_code=429)
    response = request.app.state.limiter._inject_headers(
        response, request.state.view_rate_limit
    )
    return response


app.add_exception_handler(RateLimitExceeded, _custom_rate_limit_handler)

# ── CORS ──────────────────────────────────────────────────────────────────── #
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)


# ── Security headers (Issue 016) ──────────────────────────────────────────── #
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


# ── Audit logging (Issue 017) ─────────────────────────────────────────────── #
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    # Exclude root/health checks from cluttering the audit log, if desired.
    # The spec asks to "log every request with endpoint", so we log all.
    log.info("api_request",
             endpoint=f"{request.method} {request.url.path}",
             status_code=response.status_code,
             elapsed_ms=round((time.time() - start) * 1000, 1))
    return response


from app.routers import resume_processing, auth  # noqa: E402

app.include_router(resume_processing.router)
app.include_router(auth.router, tags=["auth"])
app.include_router(ranking.router)


@app.get("/")
def read_root():
    return {"message": "Refine API is running."}


@app.get("/health")
def health_check():
    return {"status": "healthy"}
