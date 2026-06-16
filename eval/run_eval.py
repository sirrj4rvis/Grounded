"""Phase 3 deliverable: THE HEADLINE — hallucination rate before vs after
correction, on RAGTruth, with answer-quality preservation and significance.

HOW THE REDUCTION IS MEASURED WITHOUT NEW LABELS:
RAGTruth annotates hallucinations as CHARACTER SPANS inside each response. Our
corrector works by dropping unsupported sentences, so its effect is exactly
computable against those spans:

  baseline hallucinated   = response has >= 1 annotated span (ground truth)
  corrected hallucinated  = some KEPT sentence still overlaps an annotated span

Because drop-mode can only remove text, never add it, correction can only flip
examples hallucinated -> clean. The cost — the thing aggressive correction
silently breaks — is measured as:

  clean-sentence retention = fraction of sentences NOT overlapping any span
                             (ground-truth-clean) that survive correction
  abstention rate          = corrected answers with nothing left

Significance: exact McNemar / sign test on the paired per-example flips.

We sweep several thresholds around the calibrated one to expose the
reduction-vs-retention trade-off instead of cherry-picking a single point.

Run:  python -m eval.run_eval --test-size 90 --out data/correction_eval.json
"""

import argparse
import json
import os
import time
from collections import defaultdict

from eval.calibrate import stratified_sample
from eval.datasets import load_ragtruth
from verify.decompose import split_sentences_with_offsets
from verify.nli import get_verifier


def overlaps(a_start: int, a_end: int, b_start: int, b_end: int) -> bool:
    """True if [a_start, a_end) and [b_start, b_end) intersect."""
    return max(a_start, b_start) < min(a_end, b_end)


def mcnemar_exact_p(n_flips_down: int, n_flips_up: int) -> float:
    """Exact two-sided McNemar (sign) test on discordant pairs.

    Under H0 (correction has no effect) each discordant pair flips either way
    with p=0.5, so the count of down-flips ~ Binomial(n_d, 0.5). Drop-mode can
    only flip downwards, so n_flips_up is 0 by construction and the p-value is
    2 * 0.5^n_d (capped at 1). Computed by hand to stay dependency-free.
    """
    n_d = n_flips_down + n_flips_up
    if n_d == 0:
        return 1.0
    # P(X <= min) + P(X >= max) for X ~ Bin(n_d, 1/2), via symmetric tail sum.
    k = min(n_flips_down, n_flips_up)
    from math import comb

    tail = sum(comb(n_d, i) for i in range(k + 1)) / 2 ** n_d
    return min(1.0, 2 * tail)


def score_sample(verifier, examples, checkpoint_path: str | None = None):
    """Per-example sentence records: (text, start, end, support, gt_bad).

    gt_bad = the sentence overlaps an annotated hallucination span (ground
    truth). Scoring happens ONCE here; every threshold in the sweep reuses
    these scores, so the sweep itself is free.

    CHECKPOINT/RESUME (for the multi-hour full run): if checkpoint_path is
    given, each example's record is appended as a JSONL line and flushed the
    instant it's scored, so an interrupted run (sleep, crash, power loss) loses
    at most the in-flight example. Restarting with the same deterministic
    sample loads already-scored ids and skips them. Records are returned in
    `examples` order regardless of checkpoint order, so downstream
    zip(examples, records) stays aligned.
    """
    done = {}
    if checkpoint_path and os.path.exists(checkpoint_path):
        with open(checkpoint_path, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    rec = json.loads(line)
                    done[rec["id"]] = rec["sentences"]
        print(f"  resume: {len(done)} examples already in checkpoint", flush=True)

    ckpt = open(checkpoint_path, "a", encoding="utf-8") if checkpoint_path else None
    records, t0, newly = [], time.time(), 0
    try:
        for i, e in enumerate(examples, 1):
            if e.id in done:
                records.append(done[e.id])
            else:
                sents = split_sentences_with_offsets(e.response)
                supports = verifier.support_scores_multi(e.context, [s for s, _, _ in sents])
                spans = [(sp["start"], sp["end"]) for sp in e.spans]
                rec = [
                    {
                        "text": s,
                        "start": a,
                        "end": b,
                        "support": p,
                        "gt_bad": any(overlaps(a, b, sa, sb) for sa, sb in spans),
                    }
                    for (s, a, b), p in zip(sents, supports)
                ]
                records.append(rec)
                newly += 1
                if ckpt:
                    ckpt.write(json.dumps({"id": e.id, "task": e.task_type,
                                           "hallucinated": e.hallucinated, "sentences": rec}) + "\n")
                    ckpt.flush()
            if i % 15 == 0 or i == len(examples):
                rate = (time.time() - t0) / newly if newly else 0.0
                print(f"    scored {i}/{len(examples)}  ({newly} new, {rate:.1f}s/new-ex)", flush=True)
    finally:
        if ckpt:
            ckpt.close()
    return records


def evaluate_threshold(examples, records, threshold: float) -> dict:
    """Apply drop-correction at `threshold` and compute the headline numbers."""
    before, after, abstained = [], [], 0
    clean_total = clean_kept = 0
    for e, sents in zip(examples, records):
        kept = [s for s in sents if s["support"] >= threshold]
        before.append(e.hallucinated)
        after.append(any(s["gt_bad"] for s in kept))
        if not kept:
            abstained += 1
        for s in sents:
            if not s["gt_bad"]:
                clean_total += 1
                clean_kept += s["support"] >= threshold
    flips_down = sum(1 for b, a in zip(before, after) if b and not a)
    flips_up = sum(1 for b, a in zip(before, after) if not b and a)  # 0 by construction
    n = len(examples)
    return {
        "threshold": threshold,
        "rate_before": sum(before) / n,
        "rate_after": sum(after) / n,
        "flips_fixed": flips_down,
        "p_mcnemar": mcnemar_exact_p(flips_down, flips_up),
        "clean_retention": clean_kept / clean_total if clean_total else 1.0,
        "abstention_rate": abstained / n,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Baseline vs Grounded on RAGTruth.")
    ap.add_argument("--verifier", default="minicheck", choices=["minicheck", "deberta-nli"])
    ap.add_argument("--test-size", type=int, default=90)
    ap.add_argument("--thresholds", type=float, nargs="*", default=None,
                    help="support thresholds to sweep (default: calibrated + spread)")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    # Default sweep: the Phase-2 calibrated threshold plus a conservative spread.
    thresholds = args.thresholds
    if not thresholds:
        try:
            calibrated = json.load(open("data/minicheck_sentence.json"))["threshold"]
        except FileNotFoundError:
            calibrated = 0.5
        thresholds = sorted({round(t, 3) for t in (0.1, 0.25, 0.5, calibrated)})

    print(f"Loading RAGTruth test + verifier '{args.verifier}' ...")
    tst = stratified_sample(load_ragtruth(split="test"), per_task=max(1, args.test_size // 3))
    verifier = get_verifier(args.verifier)

    print(f"\nScoring {len(tst)} examples sentence-by-sentence (once; sweep is free)...")
    # Checkpoint beside the output so a long run survives interruption/resume.
    checkpoint = (args.out + ".partial.jsonl") if args.out else None
    records = score_sample(verifier, tst, checkpoint_path=checkpoint)

    rows = [evaluate_threshold(tst, records, t) for t in thresholds]

    print("\n" + "=" * 78)
    print(f"GROUNDED vs BASELINE — RAGTruth test (n={len(tst)}), drop-correction")
    print(f"{'thr':>6} | {'halluc before':>13} | {'halluc after':>12} | "
          f"{'clean kept':>10} | {'abstain':>7} | {'p (McNemar)':>11}")
    for r in rows:
        print(f"{r['threshold']:>6.3f} | {r['rate_before'] * 100:>12.1f}% | "
              f"{r['rate_after'] * 100:>11.1f}% | {r['clean_retention'] * 100:>9.1f}% | "
              f"{r['abstention_rate'] * 100:>6.1f}% | {r['p_mcnemar']:>11.2e}")
    print("=" * 78)

    if args.out:
        dump = {
            "verifier": args.verifier,
            "n": len(tst),
            "sweep": rows,
            "examples": [
                {"id": e.id, "task": e.task_type, "hallucinated": e.hallucinated,
                 "sentences": sents}
                for e, sents in zip(tst, records)
            ],
        }
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(dump, f, indent=2)
        print(f"\nWrote per-sentence scores + sweep to {args.out}")


if __name__ == "__main__":
    main()
