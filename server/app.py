"""FastAPI server: landing page, dashboard, and POST /ask -> groundedness report.

Run:  ./.venv/Scripts/python.exe -m uvicorn server.app:app --port 8000

Routes:
  GET  /          -> landing page (dashboard/landing.html)
  GET  /app       -> live demo dashboard (dashboard/index.html)
  GET  /fonts/*   -> self-hosted woff2 (static; must be served or type falls back)
  GET  /examples  -> precomputed real-RAGTruth examples (instant)
  POST /ask       -> answer + per-claim groundedness verdicts

Design notes for a CPU-only box:
  - One global Grounded pipeline, loaded lazily on first request.
  - Generation takes ~a minute on CPU; this is a demo/eval server, single worker.
"""

import json
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from pipeline import Grounded
from server.schemas import AskRequest, AskResponse

DASH_DIR = Path(__file__).resolve().parent.parent / "dashboard"

app = FastAPI(
    title="Grounded",
    description="Self-correcting RAG: answers with per-claim groundedness verdicts.",
    version="0.2.0",
)

# Serve the self-hosted fonts. Without this the @font-face URLs 404 and the
# browser silently falls back to system fonts (the custom type never applies).
app.mount("/fonts", StaticFiles(directory=str(DASH_DIR / "fonts")), name="fonts")

_pipeline: Grounded | None = None
_EXAMPLES = DASH_DIR / "demo_examples.json"


def get_pipeline() -> Grounded:
    global _pipeline
    if _pipeline is None:
        _pipeline = Grounded()
    return _pipeline


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/")
def landing() -> FileResponse:
    """Marketing/landing page — the project's pitch and headline result."""
    return FileResponse(DASH_DIR / "landing.html")


@app.get("/app")
def dashboard() -> FileResponse:
    """The live verification instrument (color-coded claims + calibration rail)."""
    return FileResponse(DASH_DIR / "index.html")


@app.get("/examples")
def examples() -> list:
    """Precomputed real-RAGTruth examples (instant; no live generation)."""
    if _EXAMPLES.exists():
        return json.loads(_EXAMPLES.read_text(encoding="utf-8"))
    return []


@app.post("/ask", response_model=AskResponse)
def ask(req: AskRequest) -> AskResponse:
    g = get_pipeline()
    # Per-request overrides without rebuilding the pipeline's loaded models.
    if req.top_k is not None:
        g.top_k = req.top_k
    if req.mode is not None:
        g.mode = req.mode
    try:
        return AskResponse(**g.ask(req.query))
    except Exception as e:  # surface Ollama/Chroma failures as a clean 503
        raise HTTPException(status_code=503, detail=f"pipeline error: {e}") from e
