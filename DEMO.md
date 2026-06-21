# Grounded — Demo Script (60–90 seconds)

The one-screen story: **type a question → watch each claim light up green (supported)
or red (unsupported) against the retrieved context → see the groundedness score and
the corrected answer.** Self-evidently "it works" to a panel or an interviewer.

> **The honest framing to keep in mind:** live generation on a CPU laptop is slow
> (~60–120 s/answer). So the demo *leads* with the instant paths (the self-playing
> hero, precomputed RAGTruth examples, the threshold slider) and shows **one** live
> answer to prove it's real. State plainly that generation is local/offline.

---

## Pre-flight checklist (do this before you hit record)

```powershell
# 1. Ollama up + model present, and PRE-WARM it (first call loads the model ~slow)
ollama serve                     # in its own terminal if not already running
ollama pull qwen2.5:3b-instruct  # only if it vanished
.venv\Scripts\python.exe -c "from rag.generator import complete; print(complete('say ok'))"

# 2. Frontend built + server running
cd frontend; npm run build; cd ..
.venv\Scripts\python.exe -m uvicorn server.app:app --host 127.0.0.1 --port 8000
```
- Open **http://localhost:8000** in a clean browser window (no clutter, hide bookmarks bar).
- **Free RAM** (close extra apps) so the one live `/ask` doesn't stall — verifier + qwen are tight on 16 GB.
- Have the question to ask **copied to clipboard** so you don't fumble typing on camera.
- Do **one throwaway live ask before recording** so the model is warm and the on-camera one is faster.

---

## The shotlist (timed)

| Time | On screen (do this) | Say this (voiceover) |
|---|---|---|
| **0:00–0:12** | Landing page. The hero **auto-plays** a claim-by-claim verification and catches a hallucination, ending on the big **34.9% → 13.1%** stat. | "RAG systems hallucinate — they state things the retrieved sources don't support. Grounded is a verification layer that catches and removes those claims." |
| **0:12–0:30** | Click into the dashboard (`/app`). Click a **"Caught hallucinations"** precomputed chip — claims render instantly, **green = supported, red = unsupported**, with a groundedness score. | "It breaks the answer into atomic claims and checks each one against the retrieved context. Green is grounded; red isn't — and here's the score." |
| **0:30–0:45** | Drag the **Calibration Rail** threshold slider. Claims reclassify live (some flip green↔red), the corrected answer updates. | "This is the calibrated threshold — the precision/recall dial. Stricter on the right drops more; looser on the left keeps more. The whole trade-off is measured, not guessed." |
| **0:45–0:58** | Switch the **corrected / annotated** toggle; expand one claim's **evidence**. | "Correction only ever *removes* unsupported claims — never invents — so 'hallucination went down' is trustworthy. Here's the exact context passage each verdict used." |
| **0:58–1:12** | In the live box, ask an **out-of-corpus** question (clipboard). It **abstains**. | "And when the answer isn't in the corpus, it says so — 'I can't answer this from the provided context' — instead of making something up. That honesty is the feature." |
| **1:12–1:30** | Ask **one in-corpus live question** (pre-warmed). Show the retrieve→generate→verify progress, then the grounded result. | "End to end on a real corpus: it cut the hallucination rate from 34.9% to 13.1% on the RAGTruth benchmark — a 63% reduction — without gutting answer quality." |

---

## Exact inputs to use (all verified to work)

- **Precomputed "Caught hallucinations" chips** (instant — the dramatic green/red): use the
  built-in dashboard examples (real RAGTruth cases). These are your money shot; no waiting.
- **Out-of-corpus (abstains):** `Who won the 2026 IPL final?` → "I can't answer this from the provided context."
- **In-corpus live (the proof it's real):** `What is photosynthesis?` or `Who was Albert Einstein?`
  (both in the Wikipedia corpus; expect a grounded answer with sources).

---

## Plan B — if live generation is too slow on the day

Cut the live `/ask` entirely and run the **all-instant** version:
1. Landing hero auto-play (0:00–0:15).
2. Two precomputed "Caught hallucinations" examples (0:15–0:45).
3. Threshold slider reclassifying claims (0:45–1:05).
4. Close on the headline stat + one line: *"generation runs locally; this is the verification layer that makes it trustworthy."*

Everything above is instant (precomputed + client-side), so the demo never stalls. You lose nothing essential — the green/red verification *is* the story.

---

## Closing line (memorize)

> "Grounded cut the hallucination rate from **34.9% to 13.1%** on RAGTruth — a **63% reduction**,
> significant at p < 1e-100 — by verifying each claim against the retrieved context, while honestly
> measuring the answer-quality trade-off. The verifier scores **AUROC 0.85**, beating a generic
> NLI baseline, and it all runs on a CPU laptop."

---

## Recording tips

- **1080p, browser zoom ~110%** so claims and the score read clearly on a projector.
- Record the landing hero **on load** (it auto-plays once) — refresh just before you hit record, or use the **Replay** button.
- Keep the cursor deliberate; pause ~1 s after each click so the viewer's eye catches the change.
- ~50–60 s is plenty if you use Plan B; budget 90 s only if you include the live ask.
- Keep a screenshot of the **trade-off figure** (`figures/tradeoff.png`) as a backup slide.
