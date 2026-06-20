# TestSprite AI Testing Report (MCP) — Grounded · Backend API

---

## 1️⃣ Document Metadata
- **Project Name:** Grounded
- **Date:** 2026-06-20
- **Type:** Backend (FastAPI) — `POST /ask`, `GET /examples`, `GET /health`, SPA + static
- **Prepared by:** TestSprite AI Team (failures verified locally)
- **Headline:** **8/10 passed (80%).** The 2 failures are **verified false positives** (wrong test assumptions), not backend defects — **0 real bugs**. Server on `127.0.0.1:8000`, dev mode.

---

## 2️⃣ Requirement Validation Summary

### Requirement: Health & examples
- **TC001 — GET /health returns service status** — ✅ Passed
- **TC002 — GET /examples returns precomputed verification examples** — ✅ Passed

### Requirement: Verify endpoint (POST /ask)
- **TC003 — /ask verifies & corrects for valid questions** — ❌ Failed → **FALSE POSITIVE (verified).**
  - The request succeeded (200; all response keys present; claims/sources well-formed). The failing line was `assert isinstance(claim["evidence"], (list, tuple))` — but `evidence` is intentionally a **string** (the closest supporting passage), per `schemas.Claim.evidence: str`, and the UI consumes it as a string. The test guessed the wrong type. **API is correct.**
- **TC004 — /ask abstains for out-of-corpus questions** — ✅ Passed (returns the abstain message, `abstained=true`).
- **TC005 — /ask validates input, 422 on invalid** — ✅ Passed (empty/missing query, out-of-range `top_k`, bad `mode` → 422).
- **TC006 — /ask returns 503 when generator unreachable** — ✅ Passed (503 mapping verified).

### Requirement: SPA + static serving
- **TC007 — GET / serves SPA shell** — ✅ Passed
- **TC008 — Unknown non-API routes return index.html** — ✅ Passed (client-side routing fallback)
- **TC009 — GET /fonts/{file} returns asset for valid woff2** — ❌ Failed → **FALSE POSITIVE (verified).**
  - The test hardcoded a non-existent filename `example-font.woff2` (the agent didn't know the real names). Real fonts (`jetbrains-mono-400.woff2`, `space-grotesk-700.woff2`, …) return **200** — verified directly. The font mount works.
- **TC010 — GET /fonts/{file} returns 404 for unknown filename** — ✅ Passed.

---

## 3️⃣ Coverage & Matching Metrics

- **Executed:** 10/10 backend tests.
- **Raw:** 8 passed · 2 failed = **80%**.
- **After verification:** both failures are test-assumption errors (string-vs-list on `evidence`; a made-up font filename). **Real backend pass rate: 10/10 behaviors correct.**

| Requirement | Total | ✅ Passed | ❌ Failed |
|---|---|---|---|
| Health & examples | 2 | 2 | 0 |
| POST /ask (verify) | 4 | 3 | 1 (false +, `evidence` is str) |
| SPA + static | 4 | 3 | 1 (false +, made-up filename) |
| **Total** | **10** | **8** | **2 (both false +)** |

---

## 4️⃣ Key Gaps / Risks

1. **No real backend defects** surfaced. Validation (422), abstain, 503 mapping, SPA fallback, examples, health, and font serving all behave correctly. (Separately, my own pre-run backend audit found and fixed one real bug — `note` missing from `AskResponse` — committed before this run.)
2. **TC003 / TC009 are test artifacts**, not code issues: `evidence` is a string (passage text), and the font test used a filename that doesn't exist. No code change warranted.
3. **`/ask` is slow + single-worker** (CPU generation ~60–120s). Backend suites must use long timeouts and avoid concurrent `/ask`. Fine for a demo; a multi-worker deploy + reachable Ollama is needed for load.
4. **No auth** by design — nothing to test there.

**Bottom line:** the backend API is correct on every tested behavior; the two red marks are wrong test expectations, confirmed by direct checks.
