# Grounded API — CPU image. Serves the verifier + dashboard.
# Generation (Ollama) is expected to run as a separate service / on the host;
# set OLLAMA_URL accordingly. For a public demo, see DEPLOY.md (precomputed mode).
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
COPY dashboard/ dashboard/
COPY pipeline.py .
COPY data/chroma/ data/chroma/
COPY data/corpus/ data/corpus/
COPY data/minicheck_sentence.json data/

# Pre-download the verifier + embedder at build time so first request is fast.
RUN python -c "from verify.nli import get_verifier; get_verifier('minicheck')" \
    && python -c "from rag.ingest import get_embedder; get_embedder()"

ENV OLLAMA_URL=http://host.docker.internal:11434
EXPOSE 8000
CMD ["uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "8000"]
