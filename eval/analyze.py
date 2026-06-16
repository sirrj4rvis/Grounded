"""Post-hoc analysis of correction_eval.json: bootstrap confidence intervals.

Reads the per-sentence scores dumped by eval/run_eval.py — no model, no CPU
cost — and reports percentile-bootstrap CIs for the headline quantities at
each threshold: rate before, rate after, absolute & relative reduction, and
clean-sentence retention.

Why bootstrap: hallucination flags are per-example Bernoullis with task-level
structure; resampling EXAMPLES (not sentences) respects that the example is
the independent unit.

Run:  python -m eval.analyze [--json data/correction_eval.json] [--iters 10000]
"""

import argparse
import json
import random


def rates_for(sample: list[dict], thr: float) -> tuple[float, float, float]:
    """(rate_before, rate_after, clean_retention) for one resample at thr."""
    n = len(sample)
    before = after = clean_total = clean_kept = 0
    for ex in sample:
        before += ex["hallucinated"]
        after += any(s["gt_bad"] for s in ex["sentences"] if s["support"] >= thr)
        for s in ex["sentences"]:
            if not s["gt_bad"]:
                clean_total += 1
                clean_kept += s["support"] >= thr
    return before / n, after / n, (clean_kept / clean_total if clean_total else 1.0)


def pct_ci(values: list[float], lo: float = 2.5, hi: float = 97.5) -> tuple[float, float]:
    v = sorted(values)
    return v[int(len(v) * lo / 100)], v[min(len(v) - 1, int(len(v) * hi / 100))]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default="data/correction_eval.json")
    ap.add_argument("--iters", type=int, default=10000)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    d = json.load(open(args.json, encoding="utf-8"))
    examples = d["examples"]
    rng = random.Random(args.seed)
    thresholds = [r["threshold"] for r in d["sweep"]]

    print(f"Bootstrap CIs (n={len(examples)}, {args.iters} resamples, 95%)\n")
    print(f"{'thr':>6} | {'before':>20} | {'after':>20} | {'rel. reduction':>20} | {'clean kept':>20}")
    for thr in thresholds:
        b0, a0, c0 = rates_for(examples, thr)
        bs = []
        for _ in range(args.iters):
            sample = [examples[rng.randrange(len(examples))] for _ in range(len(examples))]
            b, a, c = rates_for(sample, thr)
            rel = (b - a) / b if b else 0.0
            bs.append((b, a, rel, c))
        cis = [pct_ci([row[i] for row in bs]) for i in range(4)]
        rel0 = (b0 - a0) / b0 if b0 else 0.0
        cells = [
            f"{b0*100:5.1f}% [{cis[0][0]*100:4.1f},{cis[0][1]*100:5.1f}]",
            f"{a0*100:5.1f}% [{cis[1][0]*100:4.1f},{cis[1][1]*100:5.1f}]",
            f"{rel0*100:5.1f}% [{cis[2][0]*100:4.1f},{cis[2][1]*100:5.1f}]",
            f"{c0*100:5.1f}% [{cis[3][0]*100:4.1f},{cis[3][1]*100:5.1f}]",
        ]
        print(f"{thr:>6.3f} | " + " | ".join(f"{c:>20}" for c in cells))


if __name__ == "__main__":
    main()
