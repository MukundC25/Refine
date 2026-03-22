from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Refine API",
    description="Backend for the Refine resume optimization app",
    version="1.0.0"
)

# Allow CORS for local frontend development (adjust origins as needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allow all origins for local development with dynamic ports
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.routers import resume_processing, auth
from app.database import engine
from app.models import user

# Create tables
user.Base.metadata.create_all(bind=engine)

app.include_router(resume_processing.router)
app.include_router(auth.router, tags=["auth"])

@app.get("/")
def read_root():
    return {"message": "Refine API is running."}
