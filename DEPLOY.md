# Deploying Grounded — the honest free-tier story

**The real artifact is the offline evaluation**, which runs on a laptop and
produces the headline numbers + the figures in `figures/`. Record those (and a
screen capture of the color-coded dashboard) — that is what you present.

For a *public* demo, live generation on a free CPU box is too slow to be
pleasant (~a minute per answer). So there are two honest options:

## Option A — Local / offline demo (recommended for the viva)

Run everything on your machine, screen-record the dashboard answering a few
questions with claims lit green/red and the before/after correction. This is the
truthful "it works" demo; no hosting needed.

```bash
ollama serve
uvicorn server.app:app --port 8000     # open http://localhost:8000
```

## Option B — Hosted lightweight mirror

Host the **verifier + dashboard** (the cheap part) and serve **precomputed**
example results, stating plainly that generation is local/offline.

- **Container:** `docker build -t grounded . && docker run -p 8000:8000 grounded`
  The image bundles the Chroma index and the MiniCheck verifier (pre-downloaded
  at build time). Point `OLLAMA_URL` at a reachable Ollama, or run in
  precomputed mode.
- **Hugging Face Spaces (free):** push the repo with the `Dockerfile`; Spaces
  builds and serves it. CPU-only tier is fine for the verifier and the
  precomputed demo; do **not** expect fast live generation there.
- **Oracle Cloud Always-Free:** an Always-Free Ampere VM can run the container;
  same caveat on live generation speed.

### Precomputed-demo mode (the practical public demo)

Pre-run a handful of questions through `pipeline.Grounded.ask()`, save the JSON
reports, and have the dashboard load those for the demo questions — instant, and
honest about being a mirror of the offline system. (Wire this as a small
`/examples` route serving the saved reports; the live `/ask` stays available for
anyone who wants to wait for CPU generation.)

## What NOT to claim

- Don't present the cloud demo as real-time production. State: *generation is
  local/offline; the hosted demo is a lightweight mirror with precomputed
  examples.* That honesty is part of the project's credibility.
