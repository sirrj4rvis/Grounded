"""Phase 4 ablation: 1 vs N self-correction iterations (Chain-of-Verification).

WHY THIS IS A SEPARATE SCRIPT FROM run_eval.py
The headline (eval/run_eval.py) uses DROP mode because its effect is *exactly*
measurable against RAGTruth's character spans: dropping original sentences can
only flip an example hallucinated -> clean, so span-overlap still applies.
The REGENERATE loop (verify/corrector.py) instead REWRITES the answer from only
the supported sentences and re-verifies, repeating up to max_iters. Regenerated
text is new text with NO span labels, so we cannot score it against ground
truth. Claiming a ground-truth reduction on rewritten text would be dishonest.

So this ablation asks three label-free questions instead:

  1. CONVERGENCE — how many iterations does the loop actually use? `correct()`
     stops as soon as every sentence of the rewrite is supported. If most
     examples converge after ONE regenerate pass, N>1 buys little (the practical
     "1 vs N" answer). We report the distribution of iterations used and how
     often a 2nd pass changes the output at all.

  2. FAITHFULNESS (verifier proxy, sanity) — re-verify each FINAL answer. The
     corrector's final filter keeps only supported sentences, so residual
     unsupported rate should be ~0 for every mode; a non-zero value would mean
     iterating smuggled unsupported content past the filter. This is a guard,
     not a ground-truth claim.

  3. QUALITY (blind LLM-judge) — the whole point of regenerate over drop is
     fluent prose vs disjoint surviving fragments. We ask the same blind judge
     used in eval/quality_judge.py whether the regenerated answer is more
     complete/helpful than (a) the drop answer and (b) the original.

CAVEATS WE STATE, NOT HIDE: n is small (this is an ablation), the judge is a 3B
model (noisy per-example; read the aggregate), and #2/#3 are proxies, not the
RAGTruth ground truth. Temperature is 0, so regeneration is deterministic and
the max_iters=2 vs =3 comparison is exact.

Run:  python -m eval.iteration_ablation --threshold 0.25 --n 30 \
          --json data/correction_eval_full.json --out data/iteration_ablation.json
"""

import argparse
import json
import os
import random

from rag.generator import complete
from verify.corrector import ABSTAIN_MESSAGE, correct
from verify.decompose import split_sentences
from verify.nli import get_verifier
from eval.datasets import load_ragtruth
from eval.quality_judge import judge_pair


def make_regenerate_fn(task_prompt: str):
    """Closure matching pipeline.py's regenerate_fn: rewrite from supported
    facts ONLY, given the example's task. No context is passed — the supported
    sentences ARE the grounded material the rewrite is allowed to use."""

    def regenerate_fn(supported: list[str]) -> str:
        facts = "\n".join(f"- {s}" for s in supported)
        return complete(
            f"Task: {task_prompt[:1500]}\n\nVerified facts:\n{facts}\n\n"
            "Rewrite a concise answer to the task using ONLY the verified facts "
            "above. Do not add any information that is not in the facts."
        )

    return regenerate_fn


def residual_unsupported(verifier, context: str, answer: str, threshold: float) -> float:
    """Fraction of the answer's sentences the verifier still scores < threshold.
    A sanity guard: should be ~0 after correction (the final filter drops them)."""
    sents = split_sentences(answer)
    if not sents:
        return 0.0
    scores = verifier.support_scores_multi(context, sents)
    return sum(1 for p in scores if p < threshold) / len(sents)


def blind_judge(rng: random.Random, task_prompt: str, label_x: str, x: str,
                label_y: str, y: str) -> str:
    """Compare answers x and y blind (randomized A/B order). Returns label_x,
    label_y, or 'tie'. Abstentions are caller-filtered."""
    flip = rng.random() < 0.5
    a, b = (y, x) if flip else (x, y)
    verdict = judge_pair(task_prompt, a, b)
    if verdict == "TIE":
        return "tie"
    # verdict 'A' means `a` won; map back to x/y accounting for the flip.
    won_x = (verdict == "A") != flip
    return label_x if won_x else label_y


def main() -> None:
    ap = argparse.ArgumentParser(description="1-vs-N correction-iteration ablation.")
    ap.add_argument("--json", default="data/correction_eval_full.json",
                    help="per-sentence dump from run_eval.py (for sample selection)")
    ap.add_argument("--threshold", type=float, default=0.25)
    ap.add_argument("--n", type=int, default=30)
    ap.add_argument("--max-iters", type=int, default=3,
                    help="cap on correction iterations (3 = up to two regenerate passes)")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    thr = args.threshold
    dump = json.load(open(args.json, encoding="utf-8"))

    # Select the sample from the DUMP first — hallucinated examples that have
    # BOTH a supported and an unsupported sentence at this threshold (only those
    # exercise the loop: something to fix AND grounded material to rewrite from;
    # all-unsupported examples abstain in every mode). Doing selection before any
    # heavy load keeps peak RAM down on a 16 GB box.
    candidates = []
    for ex in dump["examples"]:
        if not ex["hallucinated"]:
            continue
        sup = sum(1 for s in ex["sentences"] if s["support"] >= thr)
        uns = sum(1 for s in ex["sentences"] if s["support"] < thr)
        if sup >= 1 and uns >= 1:
            candidates.append(ex)
    rng = random.Random(args.seed)
    rng.shuffle(candidates)
    candidates = candidates[: args.n]

    # Join context + task prompt back from RAGTruth, keeping ONLY the sampled ids
    # (the full test set's contexts are large; we need ~n of them). This big read
    # happens BEFORE the verifier loads so the two allocations never overlap.
    want = {ex["id"] for ex in candidates}
    rt = {e.id: e for e in load_ragtruth(split="test") if e.id in want}
    candidates = [ex for ex in candidates if ex["id"] in rt]
    print(f"ablating {len(candidates)} examples at thr={thr} "
          f"(max_iters={args.max_iters})", flush=True)

    # Pre-warm the generator so qwen is RESIDENT before the verifier loads. On a
    # 16 GB box the two models barely co-fit; the configuration that works is
    # qwen-warm-then-load-verifier (the ~3 GB free is measured WITH qwen loaded,
    # and the 1.6 GB verifier fits into it). It also prevents a mid-run qwen
    # cold-load, which OOMs (persistent 500) once the verifier holds the RAM.
    try:
        complete("Reply with the single word: ok")
        print("generator pre-warmed", flush=True)
    except Exception as e:
        print(f"prewarm failed (continuing): {e}", flush=True)

    verifier = get_verifier("minicheck")
    print("verifier loaded", flush=True)

    # Checkpoint/resume: one JSONL line per finished example.
    ckpt_path = (args.out + ".partial.jsonl") if args.out else None
    if ckpt_path:
        os.makedirs(os.path.dirname(ckpt_path) or ".", exist_ok=True)
    done = {}
    if ckpt_path and os.path.exists(ckpt_path):
        for line in open(ckpt_path, encoding="utf-8"):
            if line.strip():
                r = json.loads(line)
                done[r["id"]] = r
        print(f"  resume: {len(done)} examples already done", flush=True)
    ckpt = open(ckpt_path, "a", encoding="utf-8") if ckpt_path else None

    records = []
    for i, ex in enumerate(candidates, 1):
        if ex["id"] in done:
            records.append(done[ex["id"]])
            continue

        e = rt[ex["id"]]
        context, task_prompt = e.context, (e.meta.get("prompt") or e.response)
        original = " ".join(s["text"] for s in ex["sentences"])
        regenerate_fn = make_regenerate_fn(task_prompt)

        # Drop mode (= "1 iteration": pure removal, no regeneration).
        drop_res = correct(verifier, context, original, thr, mode="drop")

        # Regenerate up to max_iters; correct() stops early once the rewrite is
        # fully supported, so result.iterations is the convergence signal.
        regenN = correct(verifier, context, original, thr, mode="regenerate",
                          max_iters=args.max_iters, regenerate_fn=regenerate_fn)

        # Did a SECOND regenerate pass change anything? Only meaningful when the
        # loop actually ran a 2nd pass (iterations == max_iters == 3). Temp=0
        # makes the 1st pass identical, so regen@2 vs regen@3 is an exact diff.
        second_pass_changed = False
        if regenN.iterations >= 3:
            regen2 = correct(verifier, context, original, thr, mode="regenerate",
                             max_iters=2, regenerate_fn=regenerate_fn)
            second_pass_changed = regen2.corrected.strip() != regenN.corrected.strip()

        rec = {
            "id": ex["id"],
            "task": ex.get("task"),
            "iterations": regenN.iterations,
            "second_pass_changed": second_pass_changed,
            "drop_abstained": drop_res.abstained,
            "regen_abstained": regenN.abstained,
            "len_original": len(original),
            "len_drop": len(drop_res.corrected),
            "len_regen": len(regenN.corrected),
            "residual_unsupported_drop": residual_unsupported(verifier, context, drop_res.corrected, thr),
            "residual_unsupported_regen": residual_unsupported(verifier, context, regenN.corrected, thr),
        }

        # Quality (blind): only judge when neither side abstained.
        if not drop_res.abstained and not regenN.abstained:
            rec["judge_regen_vs_drop"] = blind_judge(
                rng, task_prompt, "regen", regenN.corrected, "drop", drop_res.corrected)
        if not regenN.abstained:
            rec["judge_regen_vs_original"] = blind_judge(
                rng, task_prompt, "regen", regenN.corrected, "original", original)

        records.append(rec)
        if ckpt:
            ckpt.write(json.dumps(rec) + "\n")
            ckpt.flush()
        print(f"    [{i}/{len(candidates)}] {ex['id']}: iters={rec['iterations']} "
              f"2nd-pass-changed={second_pass_changed} "
              f"regen_vs_drop={rec.get('judge_regen_vs_drop', '-')}", flush=True)

    if ckpt:
        ckpt.close()

    # ---- aggregate ----
    n = max(1, len(records))
    iters_hist = {1: 0, 2: 0, 3: 0}
    for r in records:
        iters_hist[r["iterations"]] = iters_hist.get(r["iterations"], 0) + 1
    n_2nd_changed = sum(1 for r in records if r["second_pass_changed"])

    def tally(key: str, a: str, b: str):
        w = {a: 0, b: 0, "tie": 0}
        m = 0
        for r in records:
            if key in r:
                w[r[key]] += 1
                m += 1
        return w, m

    rvd, m_rvd = tally("judge_regen_vs_drop", "regen", "drop")
    rvo, m_rvo = tally("judge_regen_vs_original", "regen", "original")
    # Residual guard is only meaningful on real (non-abstained) answers.
    live = [r for r in records if not r["regen_abstained"]]
    resid_regen = (sum(r["residual_unsupported_regen"] for r in live) / len(live)) if live else 0.0

    print("\n" + "=" * 64)
    print(f"ITERATION ABLATION — RAGTruth test, thr={thr}, n={len(records)}")
    print("-" * 64)
    print("CONVERGENCE (iterations the regenerate loop actually used):")
    print(f"  1 (no pass) : {iters_hist.get(1,0):>3}   "
          f"2 (one pass): {iters_hist.get(2,0):>3}   "
          f"3 (two pass): {iters_hist.get(3,0):>3}")
    print(f"  a 2nd pass changed the answer in {n_2nd_changed}/{len(records)} examples")
    print(f"FAITHFULNESS (residual unsupported in regen answer): {resid_regen*100:.1f}%  (expect ~0)")
    print("QUALITY (blind 3B judge):")
    print(f"  regen vs drop      (n={m_rvd}): regen {rvd['regen']}  drop {rvd['drop']}  tie {rvd['tie']}")
    print(f"  regen vs original  (n={m_rvo}): regen {rvo['regen']}  original {rvo['original']}  tie {rvo['tie']}")
    print("=" * 64)

    if args.out:
        json.dump({
            "threshold": thr, "max_iters": args.max_iters, "n": len(records),
            "convergence": iters_hist, "second_pass_changed": n_2nd_changed,
            "residual_unsupported_regen": resid_regen,
            "judge_regen_vs_drop": rvd, "judge_regen_vs_original": rvo,
            "records": records,
        }, open(args.out, "w", encoding="utf-8"), indent=2)
        print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()
