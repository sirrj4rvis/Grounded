"""Phase 4 ablation: cross-dataset generalization check on HaluEval QA.

The claim being tested: a verifier + threshold calibrated on RAGTruth still
detects hallucinations on a DIFFERENT benchmark (HaluEval) it never saw.
HaluEval QA is balanced 50/50 by construction (one faithful + one hallucinated
answer per knowledge snippet), so accuracy is meaningful and chance = 0.5.

We report, per verifier:
  - AUROC (threshold-free ranking quality) on HaluEval
  - F1 at the RAGTruth-calibrated threshold (TRANSFER — the honest number)
  - F1 at the HaluEval-optimal threshold (ceiling, for reference only)

HaluEval answers are short (usually one sentence), so whole-answer scoring is
appropriate here; this also keeps the run fast on CPU.

Run:  python -m eval.cross_dataset --verifier minicheck --limit 400
"""

import argparse
import json

from eval.calibrate import best_threshold
from eval.datasets import load_halueval_qa
from eval.metrics import detection_metrics
from verify.nli import get_verifier


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--verifier", default="minicheck", choices=["minicheck", "deberta-nli"])
    ap.add_argument("--limit", type=int, default=400, help="examples (rows x2, stays balanced)")
    ap.add_argument("--ragtruth-threshold", type=float, default=None,
                    help="default: read from data/minicheck_sentence.json")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    thr_rt = args.ragtruth_threshold
    if thr_rt is None:
        try:
            thr_rt = json.load(open("data/minicheck_sentence.json"))["threshold"]
        except FileNotFoundError:
            thr_rt = 0.5

    examples = load_halueval_qa(limit=args.limit)
    verifier = get_verifier(args.verifier)
    print(f"HaluEval QA: {len(examples)} examples | verifier={args.verifier}")

    scores, y_true = [], []
    for i, e in enumerate(examples, 1):
        scores.append(verifier.support_score(e.context, e.response))
        y_true.append(e.hallucinated)
        if i % 50 == 0 or i == len(examples):
            print(f"    scored {i}/{len(examples)}", flush=True)

    # Transfer: RAGTruth-calibrated threshold applied unchanged.
    m_transfer = detection_metrics(y_true, [s < thr_rt for s in scores],
                                   scores=[1 - s for s in scores])
    # Ceiling: threshold re-tuned on HaluEval itself (reference only — tuning
    # and testing on the same data, so do NOT quote as the headline).
    thr_best, m_best = best_threshold(y_true, scores)

    print("\n" + "=" * 60)
    print(f"CROSS-DATASET (RAGTruth -> HaluEval) — {args.verifier}")
    print(f"  AUROC                          : {m_transfer.auroc:.3f}")
    print(f"  F1 @ RAGTruth thr ({thr_rt:.3f})    : {m_transfer.f1:.3f}  ({m_transfer})")
    print(f"  F1 @ HaluEval-optimal ({thr_best:.3f}): {m_best.f1:.3f}  (ceiling, not headline)")
    print("=" * 60)

    if args.out:
        json.dump({"verifier": args.verifier, "n": len(examples),
                   "auroc": m_transfer.auroc, "thr_ragtruth": thr_rt,
                   "f1_transfer": m_transfer.f1, "thr_best": thr_best,
                   "f1_best": m_best.f1, "scores": scores, "true": y_true},
                  open(args.out, "w", encoding="utf-8"), indent=2)
        print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()
