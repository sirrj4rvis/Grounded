# Grounded — Viva & Interview Q&A

Crisp, defensible answers to the questions a panel or interviewer will actually ask.
Every number here is from the finalized evaluation ([REPORT.md](REPORT.md)). Learn the
**thesis** and the **numbers box** cold; the rest is understanding, not memorization.

> **One-sentence thesis (say this if you say nothing else):**
> *"I built a self-correcting RAG layer that cut the hallucination rate from **34.9% to
> 13.1%** on the RAGTruth benchmark — a **63% relative reduction**, p < 1e-100 — by
> decomposing answers into atomic claims and verifying each against the retrieved
> context with a calibrated checker (AUROC 0.85), while honestly measuring the
> answer-quality trade-off."*

---

## Numbers to have cold

| Thing | Number |
|---|---|
| Baseline hallucination rate (RAGTruth test, n=2,700) | **34.9%** |
| Headline (balanced, thr 0.25) | → **13.1%**, **−62.6%** [59.4–65.8], 78.5% clean kept, 2.7% abstain |
| Conservative (thr 0.10) | → 20.6%, −41.0%, **89.5%** clean kept |
| Significance | exact McNemar, **p < 1e-100**; 95% CIs = bootstrap |
| Verifier (MiniCheck, sentence-level) | **AUROC 0.854**, F1 0.57 |
| — vs whole-answer / vs DeBERTa-NLI / on HaluEval | 0.684 / 0.778 / 0.779 |
| Quality judge (n=100): balanced / conservative | original 66% vs corrected 21% / 54% vs 31% |
| Iteration ablation (n=30) | 60% need a 2nd pass; regen 12 · **drop 15** · tie 3 |

---

## Tier 1 — the four hardest (own these)

**1. Faithfulness vs factuality — what *exactly* are you measuring?**
Grounding with respect to the **retrieved context**, not world-truth. A RAG hallucination is a *faithfulness* failure: the answer asserts something the retrieved evidence doesn't support — even if it happens to be true in the world. Faithfulness is **measurable without an oracle** (compare claim ↔ retrieved passages); factuality would need a ground-truth-of-the-world oracle. RAGTruth's human labels are exactly faithfulness (spans unsupported by the *provided* source). *If pushed:* "So a true-but-unsupported claim still counts as a hallucination here — and that's the correct, measurable target for RAG."

**2. How does the NLI threshold trade precision vs recall, and how did you calibrate it?**
The verifier outputs a support probability in [0,1] per claim; a threshold τ splits supported/unsupported. **Low τ** → flag few claims unsupported (miss hallucinations — low recall); **high τ** → flag many (drop supported content — low precision). I calibrate τ by **maximizing F1 on a disjoint calibration split**, then report P/R/F1 on test. **AUROC (0.854) is threshold-free** — it measures ranking quality independent of τ. The F1-optimal τ came out **~0.10**. Crucially I don't defend one point — I **sweep τ and report the whole reduction-vs-retention curve**; the trade-off *is* the result.

**3. How do you ensure correction doesn't strip out correct information?**
I **measure it**, two ways. (a) **Clean-content retention** — the fraction of ground-truth-clean sentences (not overlapping any annotated span) that survive: **89.5%** conservative, 78.5% balanced. (b) A **blind LLM-judge** (n=100, randomized A/B) comparing original vs corrected for completeness. The honest result: there *is* a cost — the judge prefers the original 66% vs 21% at balanced, narrowing to 54% vs 31% at the conservative point. I **report the trade-off, never claim "no quality loss"** — and note the judge is completeness-biased toward the longer uncorrected answer, so it *overstates* the cost.

**4. Why a dedicated verifier (MiniCheck), not just ask the LLM "is this grounded?"**
**Calibration, speed, reproducibility.** A small purpose-built checker gives a probability I can threshold and report P/R/F1/AUROC against labels; a generic LLM self-rating is **uncalibrated** (no tunable threshold), **slow** on CPU, and **non-deterministic**. And it's empirically better: MiniCheck **AUROC 0.854** vs a generic DeBERTa-NLI baseline **0.778**, and the ranking **transfers** cross-dataset (HaluEval 0.779).

---

## Tier 2 — method & measurement follow-ups

**How did you measure a hallucination *reduction* without creating new labels?**
RAGTruth annotates hallucinations as character **spans** inside each response. My corrector works by **dropping unsupported sentences** — it only ever *removes* original text, never adds. So the effect is computable exactly against the spans: *baseline hallucinated* = response has ≥1 annotated span; *corrected hallucinated* = some **kept** sentence still overlaps a span. Drop-only means correction can only flip examples hallucinated→clean — which is precisely what makes "the rate went down" trustworthy.

**Is the reduction statistically significant?**
Yes — **exact McNemar** (sign test) on paired per-example flips, **p < 1e-100** across operating points on the full test set (n=2,700). The 95% confidence intervals are percentile **bootstrap** over examples (e.g. balanced −62.6% [59.4–65.8]).

**What is a "claim," and how do you decompose the answer?**
An atomic, individually-checkable statement. Default is a **deterministic sentence splitter** (free, reproducible); an LLM atomic-claim decomposer is the finer optional variant. Decomposition matters: verifying **sentence-by-sentence lifts MiniCheck AUROC from 0.684 (whole-answer) to 0.854** — a +0.17 jump — because MiniCheck is built for single claims and under-performs on whole multi-sentence answers.

**How does the verifier handle long contexts?**
Chunk the context into **overlapping windows** and take the **max support over windows** — a claim is grounded if *any* part of the context supports it. Without max-over-windows, long documents get artificially low scores and everything looks unsupported.

**Does the calibrated threshold transfer to other domains?**
The **ranking transfers** (MiniCheck AUROC 0.779 on HaluEval), but the **absolute threshold does not** — the RAGTruth-tuned cut-off over-flags on HaluEval (precision 0.54). Honest finding: **recalibrate the threshold per corpus**; the verifier's ordering is portable, its operating point isn't.

---

## Tier 3 — design & ablation follow-ups

**Why drop, not the regenerate / Chain-of-Verification loop?**
I **ablated it** (n=30, [REPORT §4.7](REPORT.md)). The regenerate loop genuinely iterates (**60% of cases need a 2nd pass**) and **stays faithful** (residual unsupported ≈ 0), but a blind judge **prefers drop over regenerate (15 vs 12)** — a 3B rewriter adds no quality over simply deleting unsupported sentences, at extra compute and drift-risk. So drop is the justified default: **simpler, deterministic, cheaper, exactly measurable, and no worse.**

**What happens on an out-of-corpus question — does it make something up?**
No — two defenses. The **generator** is prompted to answer *only* from context ("I don't know based on the provided context" otherwise), and the **verifier** drops unsupported claims. There's a weak cosine relevance pre-filter too, but bge-small cosine scores compress (gibberish ≈ real questions), so I'm explicit that the **verifier + generator are the real out-of-corpus defense**, not the floor. (Live demo: "2026 IPL final" → abstains.)

**Why MiniCheck specifically, and what's the baseline?**
MiniCheck (a DeBERTa-v3-Large fact-checker built for "is this claim grounded in this document") is the **primary** verifier; a generic **DeBERTa-v3 MNLI/FEVER/ANLI** model is the **baseline** for a clean ablation. Primary beats baseline on both datasets (0.854 vs 0.778 RAGTruth; 0.779 vs 0.758 HaluEval).

**Why RAGTruth? Why not build your own labelled set?**
Because a homemade set is exactly what an examiner can poke holes in. RAGTruth is a **real, labelled, RAG-specific** hallucination corpus (span-level, across QA / Summarization / Data-to-text). My contribution is the **verification system and the measured reduction**, not a new dataset. **HaluEval** is the cross-dataset generalization check (and comes out exactly 50% hallucinated by construction — a built-in correctness check on my label mapping).

---

## Tier 4 — limitations & "what next" (showing maturity)

**What's the biggest limitation?**
The **quality cost is real** — correction trades completeness for groundedness, so I never claim "no quality loss"; the lesson is **operating-point selection** (the conservative threshold buys a −41% reduction at 89.5% retention for far less quality cost). Secondary: the **threshold is domain-specific**, and **decomposition on a 3B model** imperfectly decontextualizes claims (a pronoun sometimes survives and the claim becomes unverifiable).

**What would you do with more compute / a GPU?**
A **stronger rewriter** for the regenerate loop (a 3B rewriter didn't beat drop — a larger one might), **re-retrieval on unsupported claims** to *recover* content instead of only removing it, a **distilled atomic-claim decomposer**, and larger judge samples for tighter quality CIs.

**How does this run on a CPU laptop at all?**
Everything is **inference on small models** — qwen2.5:3b via Ollama, bge-small embeddings, MiniCheck/DeBERTa verifiers — no GPU, no fine-tuning. Evaluation is **offline/batch**. And the headline is a measured reduction on a public benchmark, so it's **hardware-independent** — the result holds regardless of the machine it was produced on.

**If the reduction had been small, would the project have failed?**
No — it survives as a **calibrated hallucination *detector*** with measured detection quality (AUROC 0.85, validated cross-dataset), which is itself a defensible, demoable result. The detector and the reducer share the same verifier; the color-coded UI works either way.

---

## Three interview stories this unlocks

- **System design** — "design a RAG system that doesn't hallucinate": I built and *measured* one; I can talk retrieval → generation → claim decomposition → calibrated verification → correction → abstain.
- **Debugging / trade-off** — claim-decomposition noise and the precision/recall threshold calibration; the honest quality-cost trade-off; why I chose drop over regenerate via an ablation.
- **Measurement integrity** — how I established a credible hallucination metric on a real benchmark (span-overlap on drop-only correction, McNemar significance, bootstrap CIs) and avoided fooling myself (blind judge, disjoint calibration split, cross-dataset check).
