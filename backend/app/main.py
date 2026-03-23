from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

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
    lifespan=lifespan
)

# Allow CORS for all origins (needed for Render deployment)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.routers import resume_processing, auth

app.include_router(resume_processing.router)
app.include_router(auth.router, tags=["auth"])

@app.get("/")
def read_root():
    return {"message": "Refine API is running."}

@app.get("/health")
def health_check():
    return {"status": "healthy"}
