# Grounded — Runbook

Operational guide for running, configuring, evaluating, deploying, and troubleshooting
Grounded (self-correcting RAG verification layer). CPU-only, fully local, ₹0.

> **TL;DR — start the demo:** Ollama running with `qwen2.5:3b-instruct`, the corpus ingested,
> the frontend built, then `uvicorn server.app:app --host 127.0.0.1 --port 8000` → open
> http://localhost:8000.

---

## 1. Architecture (what runs)

```
Browser ──HTTP──> FastAPI (server/app.py, port 8000)
                    ├─ serves the built React SPA (frontend/dist)   [landing + dashboard]
                    ├─ GET  /examples   precomputed RAGTruth examples (instant)
                    └─ POST /ask        pipeline.Grounded.ask():
                           retrieve (Chroma + BM25, rag/retriever.py)
                         → generate    (Ollama qwen2.5:3b, rag/generator.py)
                         → verify       (MiniCheck DeBERTa, verify/nli.py)
                         → correct      (drop/flag/regenerate, verify/corrector.py)
                         → abstain if out-of-corpus / unsupported
```
- **Generator** (Ollama) is the only external process; everything else is in-process Python.
- **Vector store** is a local ChromaDB at `data/chroma/` (rebuilt by `rag/ingest.py`).
- Benchmark numbers come from `eval/` over RAGTruth/HaluEval — independent of the live demo.

---

## 2. Prerequisites

| Need | Version / notes |
|---|---|
| Python | 3.12+ (local venv uses 3.14; Docker uses 3.12-slim) |
| Node | 22+ (for the Vite frontend build) |
| Ollama | running locally; model `qwen2.5:3b-instruct` pulled |
| RAM | 16 GB is enough **but tight** — see Troubleshooting (don't run Docker + an 8B model + the verifier at once) |
| GPU | none required (CPU-only) |

---

## 3. First-time setup

```powershell
# from d:\Grounded
py -3.12 -m venv .venv                       # or py -3.14
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

# generator model (CPU)
ollama serve                                 # in its own terminal (or it runs as a service)
ollama pull qwen2.5:3b-instruct

# build the corpus index (see §5 for corpus choice)
# fast 4-doc demo corpus:
$env:GROUNDED_CORPUS="local"; .\.venv\Scripts\python.exe -m rag.ingest
#   OR the broad ~4000-article Wikipedia corpus (~70 min on CPU):
# .\.venv\Scripts\python.exe -m rag.ingest

# build the frontend
cd frontend; npm install; npm run build; cd ..
```

---

## 4. Running

### Production mode (one server, one URL) — recommended for demos
```powershell
.\.venv\Scripts\python.exe -m uvicorn server.app:app --host 127.0.0.1 --port 8000
```
Open **http://localhost:8000**. FastAPI serves the built SPA **and** the API. Ctrl+C to stop.
> Use `127.0.0.1`, **not** `localhost` (see Troubleshooting — IPv4/IPv6).

### Dev mode (hot-reload for UI work) — two terminals
```powershell
# terminal 1 — backend API
.\.venv\Scripts\python.exe -m uvicorn server.app:app --host 127.0.0.1 --port 8000
# terminal 2 — Vite dev server (proxies /ask, /examples to :8000)
cd frontend; npm run dev          # open the URL Vite prints (http://localhost:5173)
```

### CLI (no browser)
```powershell
.\.venv\Scripts\python.exe scripts\ask.py "Why did the Emu War fail?"
```

---

## 5. The corpus

Ingestion (`rag/ingest.py`) is configurable via env and rebuilds `data/chroma/`:

| `GROUNDED_CORPUS` | Source | Size / time |
|---|---|---|
| `local` | 4 demo docs in `data/corpus/` | 4 chunks, seconds |
| `wikipedia` (default) | `wikimedia/wikipedia` `20231101.simple`, first 4000 articles | ~22k chunks, **~70 min** CPU embed |

```powershell
$env:GROUNDED_CORPUS="wikipedia"; $env:GROUNDED_WIKI_LIMIT="4000"
.\.venv\Scripts\python.exe -m rag.ingest      # streams + batch-embeds; prints progress
```
Re-ingesting fully rebuilds the index. The retriever loads it on the **first** `/ask` (or at
`HybridRetriever()` construction).

---

## 6. Configuration (environment variables)

| Variable | Default | Purpose |
|---|---|---|
| `OLLAMA_URL` | `http://127.0.0.1:11434` | Ollama endpoint (use 127.0.0.1, not localhost) |
| `GROUNDED_GEN_MODEL` | `qwen2.5:3b-instruct` | generator model; fallback: `llama3.1:latest` (8B, slower) |
| `GROUNDED_CORPUS` | `wikipedia` | `wikipedia` \| `local` |
| `GROUNDED_WIKI_DATASET` / `_CONFIG` / `_LIMIT` | `wikimedia/wikipedia` / `20231101.simple` / `4000` | corpus source/size |
| `GROUNDED_RELEVANCE_FLOOR` | `0.40` | out-of-corpus pre-filter (weak signal; verifier is the real defense) |
| `GROUNDED_LOW_PRIORITY` | unset | `1` runs verifier processes at below-normal CPU priority (for long offline runs) |

PowerShell sets env per-session with `$env:NAME="value"` before the command.

---

## 7. Verify it works (smoke test)

```powershell
# health (expect: {"status":"ok","frontend":"react"})
.\.venv\Scripts\python.exe -c "import requests;print(requests.get('http://127.0.0.1:8000/health',timeout=5).json())"

# examples (expect: 3)
.\.venv\Scripts\python.exe -c "import requests;print(len(requests.get('http://127.0.0.1:8000/examples',timeout=5).json()))"
```
Then in the UI:
- **In-corpus** (grounded): "What is photosynthesis?", "Who was Albert Einstein?", "What is gravity?"
- **Out-of-corpus** (abstains): "Who won the 2026 IPL final?" → *"I can't answer this from the provided context."*
- Drag the **threshold** slider to watch claims flip supported/dropped.

Full test sweeps (what was used to validate): backend = import + logic + API-surface checks;
frontend = Playwright over interactions/console/mobile/reduced-motion. Both green.

---

## 8. Evaluation (reproduce the benchmark numbers)

```powershell
.\.venv\Scripts\python.exe -m eval.baseline                       # baseline hallucination rate
.\.venv\Scripts\python.exe -m eval.calibrate --method sentence    # verifier P/R/F1/AUROC
.\.venv\Scripts\python.exe -m eval.run_eval --test-size 2700 --out data\correction_eval_full.json
.\.venv\Scripts\python.exe -m eval.analyze --json data\correction_eval_full.json   # bootstrap CIs
.\.venv\Scripts\python.exe -m eval.figures                        # report figures -> figures/
```
- Long runs **checkpoint** to `<out>.partial.jsonl` and resume if re-run with the same args.
- Headline: RAGTruth hallucination **34.9% → 13.1%** (balanced threshold), full curve in `REPORT.md`.

---

## 9. Docker

```powershell
docker build -t grounded .
docker run -d -p 8000:8000 --name grounded grounded     # http://localhost:8000
```
- Multi-stage: Node builds the SPA → Python serves it + the API; the image builds the index and
  pre-loads the verifier so first request is fast.
- The image uses `GROUNDED_CORPUS=local` (the Wikipedia embed is too slow for a build).
- **Caveats:** image is ~9.5 GB (PyTorch + models) — too big for most free tiers; live `/ask`
  needs Ollama reachable at `OLLAMA_URL` (set `OLLAMA_HOST=0.0.0.0` on the host so the container
  can reach it via `host.docker.internal`). Examples + landing + threshold work without Ollama.
- See `DEPLOY.md` for the honest free-tier / precomputed-mirror story.

---

## 10. Troubleshooting (the real gotchas)

| Symptom | Cause → Fix |
|---|---|
| `/ask` → 503, log `404 ... /api/generate "model not found"` | `qwen2.5:3b-instruct` not installed (it has vanished here before) → `ollama pull qwen2.5:3b-instruct`. Or use the fallback: `$env:GROUNDED_GEN_MODEL="llama3.1:latest"`. |
| `/ask` → can't reach Ollama / connection refused | The Ollama **server** isn't running (the tray "ollama app" ≠ the server) → `ollama serve`. If "address already in use", `Get-Process ollama* \| Stop-Process -Force` then `ollama serve`. |
| Model present in `ollama list` but `/ask` still 404s | **IPv4/IPv6**: `localhost` resolves to `::1`, a different Ollama instance. Always use **`127.0.0.1`** (the generator default already does). |
| `RuntimeError: ... DefaultCPUAllocator: not enough memory` (OOM) | Too much loaded at once on 16 GB → stop Docker (`Get-Process 'Docker Desktop',com.docker.* \| Stop-Process -Force; wsl --shutdown`), unload big models (`ollama stop llama3.1:latest`), prefer the 3B qwen over 8B. |
| `docker build` → "failed to connect to the docker API" | Docker Desktop engine not running → start Docker Desktop (click "Stop processes" if it warns about lingering processes), wait for the steady whale icon. |
| `docker run` → "ports are not available / address in use" | Port taken → use another host port: `docker run -p 8080:8000 ...`. |
| Custom fonts not rendering (system fallback) | `/fonts/*` must be served — it is, via the StaticFiles mount in `server/app.py`. Rebuild the frontend if `frontend/dist/fonts/` is missing. |
| Live `/ask` feels frozen | It's slow on CPU (~60–120s); the **first** request also loads the model. The UI shows a `retrieve → generate → verify` progress + elapsed timer. Don't fire concurrent `/ask` (single worker). |
| PowerShell `Invoke-WebRequest`/`Invoke-RestMethod` hangs or errors "NonInteractive mode" | Use the venv Python + `requests`, or `curl`, instead. |
| Out-of-corpus question returns an odd grounded answer instead of abstaining | The corpus may have a tangentially-related article. This is faithfulness (grounded ≠ helpful); the verifier still drops unsupported claims. Broaden/swap the corpus if needed. |

---

## 11. File map

```
rag/        ingest.py (corpus→Chroma) · retriever.py (BM25+dense, relevance) · generator.py (Ollama)
verify/     decompose.py (claims) · nli.py (MiniCheck/DeBERTa) · corrector.py (drop/flag/regenerate)
pipeline.py Grounded.ask() — the live path
server/     app.py (FastAPI: SPA + /ask + /examples + /health) · schemas.py (Pydantic)
frontend/   React + Vite + Tailwind + framer-motion (src/pages/{Landing,Dashboard}.tsx); build → dist/
eval/       datasets · metrics · baseline · calibrate · run_eval · analyze · cross_dataset · quality_judge · figures
data/       corpus/ (local docs) · chroma/ (index, gitignored) · *.json (eval results)
Dockerfile · DEPLOY.md · REPORT.md · README.md · RUNBOOK.md (this file)
```
