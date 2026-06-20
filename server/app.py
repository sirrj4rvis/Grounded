"""FastAPI server: serves the React SPA + the verification API.

Run:  ./.venv/Scripts/python.exe -m uvicorn server.app:app --host 127.0.0.1 --port 8000
Build the frontend first:  cd frontend && npm run build   (outputs frontend/dist/)

Routes:
  GET  /examples  -> precomputed real-RAGTruth examples (instant)
  POST /ask       -> answer + per-claim groundedness verdicts (slow, CPU generation)
  GET  /health    -> health check
  GET  /assets/*  -> built JS/CSS (Vite)         |  GET /fonts/* -> self-hosted woff2
  GET  /*         -> SPA fallback (index.html) for client-side routes (/, /app, ...)

If frontend/dist is absent (frontend not built), falls back to the legacy static
dashboard so the server still runs.
"""

import json
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from pipeline import Grounded
from server.schemas import AskRequest, AskResponse

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "frontend" / "dist"
LEGACY = ROOT / "dashboard"
SPA = (DIST / "index.html").exists()

app = FastAPI(title="Grounded", description="Self-correcting RAG with per-claim verification.", version="0.3.0")

_pipeline: Grounded | None = None
_EXAMPLES = LEGACY / "demo_examples.json"


def get_pipeline() -> Grounded:
    global _pipeline
    if _pipeline is None:
        _pipeline = Grounded()
    return _pipeline


# ── API routes (defined before the SPA catch-all so they take precedence) ──
@app.get("/health")
def health() -> dict:
    return {"status": "ok", "frontend": "react" if SPA else "legacy"}


@app.get("/examples")
def examples() -> list:
    """Precomputed real-RAGTruth examples (instant; no live generation)."""
    if _EXAMPLES.exists():
        return json.loads(_EXAMPLES.read_text(encoding="utf-8"))
    return []


@app.post("/ask", response_model=AskResponse)
def ask(req: AskRequest) -> AskResponse:
    g = get_pipeline()
    if req.top_k is not None:
        g.top_k = req.top_k
    if req.mode is not None:
        g.mode = req.mode
    try:
        return AskResponse(**g.ask(req.query))
    except Exception as e:  # surface Ollama/Chroma failures as a clean 503
        raise HTTPException(status_code=503, detail=f"pipeline error: {e}") from e


# ── Static assets + SPA ────────────────────────────────────────────────────
if SPA:
    app.mount("/assets", StaticFiles(directory=str(DIST / "assets")), name="assets")
    app.mount("/fonts", StaticFiles(directory=str(DIST / "fonts")), name="fonts")

    @app.get("/{full_path:path}")
    def spa(full_path: str) -> FileResponse:
        """Serve the SPA shell for any non-API path (client-side routing)."""
        return FileResponse(DIST / "index.html")
else:
    # Legacy fallback: the original static dashboard (pre-React build).
    app.mount("/fonts", StaticFiles(directory=str(LEGACY / "fonts")), name="fonts")

    @app.get("/")
    def legacy_landing() -> FileResponse:
        return FileResponse(LEGACY / "landing.html")

    @app.get("/app")
    def legacy_app() -> FileResponse:
        return FileResponse(LEGACY / "index.html")
