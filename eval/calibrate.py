"""Phase 2 deliverable: calibrate the verifier's threshold and measure its
detection quality on RAGTruth.

This is WHOLE-ANSWER verification (the coarse start the plan calls for): we
score each full response against its full context, then threshold the support
score to predict hallucinated / grounded. Claim decomposition comes later as an
improvement + ablation.

WHERE THE "CALIBRATION" RIGOR LIVES:
  - The verifier emits a continuous support score in [0, 1]. AUROC measures its
    ranking quality independent of any threshold.
  - We then choose the support threshold that maximises F1 on a CALIBRATION
    split (drawn from RAGTruth train) and report P/R/F1 at that threshold on a
    disjoint TEST split. Tuning and reporting on disjoint data is what keeps the
    reported F1 honest.
  - hallucinated  <=>  support_score < threshold.

Sampling is stratified by task_type so QA / Summary / Data2txt are all
represented. CPU inference is ~seconds per example, so default sample sizes are
modest; pass larger --cal-size / --test-size for the full offline run.

Run:  python -m eval.calibrate --verifier minicheck --cal-size 150 --test-size 150
"""

import argparse
import json
import random
import time
from collections import defaultdict

from eval.datasets import load_ragtruth
from eval.metrics import detection_metrics
from verify.decompose import decompose, split_sentences
from verify.nli import get_verifier


def response_support(verifier, ctx: str, response: str, method: str) -> float:
    """Response-level support under a decomposition method (the core ablation).

      whole    - support for the full response as one unit (coarse baseline)
      sentence - min over sentence supports (deterministic, fast)
      llm      - min over LLM atomic-claim supports (finer, slower)

    Decomposed methods take the MIN over units: a response is only as grounded
    as its weakest claim, mirroring "any unsupported span => response unfaithful".
    """
    if method == "whole":
        return verifier.support_score(ctx, response)
    units = split_sentences(response) if method == "sentence" else decompose(response)
    if not units:
        return verifier.support_score(ctx, response)
    # Batched: all units' (window, claim) pairs go through together, then MIN
    # over units — a response is only as grounded as its weakest claim.
    return min(verifier.support_scores_multi(ctx, units))


def stratified_sample(examples, per_task: int, seed: int = 0):
    """Take up to `per_task` examples per task_type, by SEEDED RANDOM sampling.

    Reproducible (fixed seed) but representative: an earlier version sorted by
    `e.id` and took an even stride, but ids are strings ("0","1","10",...) and
    RAGTruth orders responses in per-model blocks, so the lexical stride
    oversampled the low-hallucination models and badly skewed class balance
    (Data2txt sample 18% positive vs 64% true). Random sampling per task tracks
    the true prevalence in expectation, which the calibrated threshold needs.
    """
    by_task = defaultdict(list)
    for e in examples:
        by_task[e.task_type].append(e)
    rng = random.Random(seed)
    sample = []
    for task, items in sorted(by_task.items()):
        items = sorted(items, key=lambda e: e.id)  # stable order before sampling
        if len(items) <= per_task:
            sample.extend(items)
        else:
            sample.extend(rng.sample(items, per_task))
    return sample


def score_examples(verifier, examples, method: str = "whole"):
    """Return support scores aligned with `examples` (with progress + timing)."""
    scores, t0 = [], time.time()
    for i, e in enumerate(examples, 1):
        scores.append(response_support(verifier, e.context, e.response, method))
        if i % 25 == 0 or i == len(examples):
            rate = (time.time() - t0) / i
            print(f"    scored {i}/{len(examples)}  ({rate:.1f}s/ex)", flush=True)
    return scores


def best_threshold(y_true, support_scores):
    """Pick the support threshold maximising hallucination-detection F1.

    Candidate thresholds are the midpoints between sorted unique scores, so we
    test every distinct way of splitting the data. Returns (threshold, metrics).
    """
    uniq = sorted(set(support_scores))
    candidates = [(uniq[i] + uniq[i + 1]) / 2 for i in range(len(uniq) - 1)] or [0.5]

    best = None
    for thr in candidates:
        y_pred = [s < thr for s in support_scores]  # low support => hallucinated
        m = detection_metrics(y_true, y_pred)
        if best is None or m.f1 > best[1].f1:
            best = (thr, m)
    return best


def main() -> None:
    ap = argparse.ArgumentParser(description="Calibrate the verifier on RAGTruth.")
    ap.add_argument("--verifier", default="minicheck", choices=["minicheck", "deberta-nli"])
    ap.add_argument("--method", default="whole", choices=["whole", "sentence", "llm"],
                    help="decomposition method (whole-answer vs claim-level ablation)")
    ap.add_argument("--cal-size", type=int, default=150, help="calibration examples (from train)")
    ap.add_argument("--test-size", type=int, default=150, help="test examples (from test split)")
    ap.add_argument("--out", default=None, help="optional JSON path to dump scores+metrics")
    args = ap.parse_args()

    print(f"Loading RAGTruth + verifier '{args.verifier}' ...")
    train = load_ragtruth(split="train")
    test = load_ragtruth(split="test")
    cal = stratified_sample(train, per_task=max(1, args.cal_size // 3))
    tst = stratified_sample(test, per_task=max(1, args.test_size // 3))
    verifier = get_verifier(args.verifier)

    print(f"\nScoring calibration set ({len(cal)} ex)...")
    cal_scores = score_examples(verifier, cal, args.method)
    cal_true = [e.hallucinated for e in cal]
    thr, cal_m = best_threshold(cal_true, cal_scores)
    # AUROC uses the hallucination score (1 - support) so higher = more hallucinated.
    cal_auroc = detection_metrics(cal_true, [s < thr for s in cal_scores],
                                  scores=[1 - s for s in cal_scores]).auroc

    print(f"\nScoring test set ({len(tst)} ex)...")
    tst_scores = score_examples(verifier, tst, args.method)
    tst_true = [e.hallucinated for e in tst]
    tst_m = detection_metrics(tst_true, [s < thr for s in tst_scores],
                              scores=[1 - s for s in tst_scores])

    print("\n" + "=" * 64)
    print(f"VERIFIER: {args.verifier}   (method: {args.method})")
    print(f"Calibrated threshold (max-F1 on calibration): support < {thr:.3f} => hallucinated")
    print(f"  calibration: {cal_m}  AUROC={cal_auroc:.3f}")
    print(f"  TEST       : {tst_m}")
    print("=" * 64)

    # Per-task test breakdown — Data2txt is expected to be hardest.
    print("  test F1 by task_type:")
    by_task = defaultdict(lambda: ([], []))
    for e, s in zip(tst, tst_scores):
        yt, sc = by_task[e.task_type]
        yt.append(e.hallucinated)
        sc.append(s)
    for task, (yt, sc) in sorted(by_task.items()):
        m = detection_metrics(yt, [s < thr for s in sc])
        print(f"    {task:<10} {m}")

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "verifier": args.verifier,
                    "threshold": thr,
                    "test": {"ids": [e.id for e in tst], "support": tst_scores,
                             "true": tst_true},
                    "test_metrics": tst_m.__dict__,
                },
                f,
                indent=2,
            )
        print(f"\nWrote scores+metrics to {args.out}")


if __name__ == "__main__":
    main()
