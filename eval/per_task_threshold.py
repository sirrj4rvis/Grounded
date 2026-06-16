"""Per-task thresholds vs one global threshold — fixing the recurring weak link.

Throughout the project a SINGLE global support threshold over-flagged the
low-prevalence tasks (QA/Summary): it's dominated by high-prevalence Data2txt,
so it sits too high for the others and drops their clean sentences. This tests
the fix — calibrate a SEPARATE threshold per task_type.

Rigor: the full-test per-sentence scores (from run_eval.py) are split into
disjoint CAL/EVAL halves, stratified by task and seeded. Thresholds are chosen
on CAL only; every number is reported on EVAL. No model, no GPU — pure analysis
on already-computed scores.

Two views on EVAL:
  1. Sentence-level detection F1 (positive = unsupported sentence), global vs
     per-task — does per-task thresholding raise precision on QA/Summary?
  2. Downstream drop-correction: hallucination reduction + clean retention,
     global vs per-task — does it improve the practical trade-off?

Run:  python -m eval.per_task_threshold --json data/correction_eval_full.json
"""

import argparse
import json
import random
from collections import defaultdict

from eval.metrics import detection_metrics


def split_cal_eval(examples, seed: int = 0):
    """Disjoint CAL/EVAL halves, stratified by task, deterministic."""
    by_task = defaultdict(list)
    for e in examples:
        by_task[e["task"]].append(e)
    rng = random.Random(seed)
    cal, ev = [], []
    for _, items in sorted(by_task.items()):
        items = sorted(items, key=lambda e: e["id"])
        rng.shuffle(items)
        half = len(items) // 2
        cal.extend(items[:half])
        ev.extend(items[half:])
    return cal, ev


def sentence_rows(examples):
    """Flatten to (task, support, gt_bad) over every sentence."""
    return [(e["task"], s["support"], s["gt_bad"]) for e in examples for s in e["sentences"]]


def best_threshold(rows) -> float:
    """Support threshold maximising sentence-detection F1 (positive = unsupported).

    rows: list of (support, gt_bad). Predict unsupported if support < thr.
    """
    supports = sorted({s for s, _ in rows})
    candidates = [(supports[i] + supports[i + 1]) / 2 for i in range(len(supports) - 1)] or [0.5]
    best_thr, best_f1 = 0.5, -1.0
    for thr in candidates:
        y_true = [b for _, b in rows]
        y_pred = [s < thr for s, _ in rows]
        f1 = detection_metrics(y_true, y_pred).f1
        if f1 > best_f1:
            best_thr, best_f1 = thr, f1
    return best_thr


def task_f1(rows, thr_fn) -> dict:
    """Per-task and overall detection F1 on rows under thr_fn(task)->threshold."""
    by_task = defaultdict(lambda: ([], []))
    for task, support, bad in rows:
        yt, yp = by_task[task]
        yt.append(bad)
        yp.append(support < thr_fn(task))
    out = {t: detection_metrics(yt, yp).f1 for t, (yt, yp) in sorted(by_task.items())}
    all_t = [b for _, _, b in rows]
    all_p = [s < thr_fn(t) for t, s, b in rows]
    out["OVERALL"] = detection_metrics(all_t, all_p).f1
    return out


def correction_outcome(examples, thr_fn) -> dict:
    """Drop-correction hallucination reduction + clean retention under thr_fn."""
    n = len(examples)
    before = after = abstained = clean_total = clean_kept = 0
    for e in examples:
        thr = thr_fn(e["task"])
        kept = [s for s in e["sentences"] if s["support"] >= thr]
        before += e["hallucinated"]
        after += any(s["gt_bad"] for s in kept)
        if not kept:
            abstained += 1
        for s in e["sentences"]:
            if not s["gt_bad"]:
                clean_total += 1
                clean_kept += s["support"] >= thr
    return {
        "rate_before": before / n,
        "rate_after": after / n,
        "clean_retention": clean_kept / clean_total if clean_total else 1.0,
        "abstention": abstained / n,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default="data/correction_eval_full.json")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default="data/per_task_threshold.json")
    args = ap.parse_args()

    examples = json.load(open(args.json, encoding="utf-8"))["examples"]
    cal, ev = split_cal_eval(examples, args.seed)
    cal_rows, ev_rows = sentence_rows(cal), sentence_rows(ev)

    # Choose thresholds on CAL only.
    global_thr = best_threshold([(s, b) for _, s, b in cal_rows])
    per_task_thr = {}
    for task in sorted({t for t, _, _ in cal_rows}):
        per_task_thr[task] = best_threshold([(s, b) for t, s, b in cal_rows if t == task])

    g_fn = lambda _t: global_thr
    p_fn = lambda t: per_task_thr[t]

    print(f"Calibrated on {len(cal)} ex, evaluated on {len(ev)} ex (disjoint).\n")
    print(f"Global threshold      : {global_thr:.3f}")
    print("Per-task thresholds   : " + ", ".join(f"{t}={v:.3f}" for t, v in per_task_thr.items()))

    gf, pf = task_f1(ev_rows, g_fn), task_f1(ev_rows, p_fn)
    print("\nSentence-detection F1 on EVAL (positive = unsupported sentence):")
    print(f"  {'task':<10} {'global':>8} {'per-task':>10} {'delta':>8}")
    for t in [k for k in pf if k != "OVERALL"] + ["OVERALL"]:
        print(f"  {t:<10} {gf[t]:>8.3f} {pf[t]:>10.3f} {pf[t] - gf[t]:>+8.3f}")

    go, po = correction_outcome(ev, g_fn), correction_outcome(ev, p_fn)
    print("\nDrop-correction outcome on EVAL:")
    print(f"  {'scheme':<10} {'halluc after':>12} {'clean kept':>11} {'abstain':>8}")
    for name, o in (("global", go), ("per-task", po)):
        print(f"  {name:<10} {o['rate_after']*100:>11.1f}% {o['clean_retention']*100:>10.1f}% "
              f"{o['abstention']*100:>7.1f}%")
    print(f"  (baseline hallucination before = {go['rate_before']*100:.1f}%)")

    json.dump({"global_threshold": global_thr, "per_task_thresholds": per_task_thr,
               "eval_f1_global": gf, "eval_f1_per_task": pf,
               "correction_global": go, "correction_per_task": po},
              open(args.out, "w", encoding="utf-8"), indent=2)
    print(f"\nWrote {args.out}")


if __name__ == "__main__":
    main()
