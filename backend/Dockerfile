FROM python:3.11.9-slim

WORKDIR /app

# Build deps for sentence-transformers / psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# CPU-only torch first (avoids pulling the ~2 GB CUDA wheel)
RUN pip install --no-cache-dir torch==2.3.1 \
    --index-url https://download.pytorch.org/whl/cpu

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Bake the sentence-transformer model into the image so the container
# can run with --network none during the challenge ranking run.
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

EXPOSE 8000

# PYTHONPATH lets uvicorn resolve both `app.*` and `backend.app.*` imports.
ENV PYTHONPATH=/app:/app/..

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
