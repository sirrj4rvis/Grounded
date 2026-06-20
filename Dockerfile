# Grounded — multi-stage image: build the React SPA with Node, serve it + the
# verification API with Python. Generation (Ollama) runs as a separate service;
# set OLLAMA_URL accordingly. For a public demo see DEPLOY.md (precomputed mode).

# ── Stage 1: build the React frontend (Vite) ──────────────────────────────
FROM node:22-slim AS frontend
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build            # -> /frontend/dist

# ── Stage 2: Python app serving the built SPA + the API ───────────────────
FROM python:3.12-slim
WORKDIR /app

# System deps for sentencepiece / tokenizers wheels.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
# CPU-only torch keeps the image small (no CUDA).
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir -r requirements.txt

COPY rag/ rag/
COPY verify/ verify/
COPY eval/ eval/
COPY server/ server/
COPY pipeline.py .
COPY data/corpus/ data/corpus/
COPY data/minicheck_sentence.json data/
COPY dashboard/demo_examples.json dashboard/

# Built SPA from stage 1 (server/app.py serves frontend/dist as the SPA).
COPY --from=frontend /frontend/dist frontend/dist

# Build the vector index, and pre-download the verifier + embedder, at build
# time so the container starts ready and the first request is fast.
RUN python -m rag.ingest \
    && python -c "from verify.nli import get_verifier; get_verifier('minicheck')" \
    && python -c "from rag.ingest import get_embedder; get_embedder()"

ENV OLLAMA_URL=http://host.docker.internal:11434
EXPOSE 8000
CMD ["uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "8000"]
