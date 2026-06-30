import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Ranking system paths (Issue 013). All relative to repo root by default.
EMBEDDINGS_PATH = os.getenv("EMBEDDINGS_PATH", "./precomputed/embeddings.npy")
CANDIDATE_IDS_PATH = os.getenv("CANDIDATE_IDS_PATH", "./precomputed/candidate_ids.json")
CANDIDATES_JSONL_PATH = os.getenv("CANDIDATES_JSONL_PATH", "./candidates.jsonl")
PARSED_JD_CACHE_PATH = os.getenv("PARSED_JD_CACHE_PATH", "./precomputed/parsed_jd.json")
RICH_REASONING_PATH = os.getenv("RICH_REASONING_PATH", "./precomputed/rich_reasoning.json")
EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "all-MiniLM-L6-v2")
