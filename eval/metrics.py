"""Metrics for Grounded.

WHAT WE MEASURE: faithfulness / groundedness. A "hallucination" is a response
(or claim) NOT supported by its retrieved CONTEXT — regardless of whether it
happens to be true in the world. Every label and prediction below is with
respect to the provided context, never world-truth. This is the well-defined,
measurable target the project defends.

Two families of metric live here:
  1. hallucination_rate  — prevalence of unsupported responses in a set. This
     is the BASELINE number (and, post-correction, the reduced number).
  2. detection_metrics   — how well a verifier flags hallucinations, scored
     against ground-truth labels. POSITIVE CLASS = hallucinated (the thing we
     want to catch), so recall = "fraction of real hallucinations we caught"
     and precision = "of what we flagged, how much was really hallucinated."

Answer-quality preservation (Phase 3) is deliberately NOT here yet — it needs
the corrector's outputs to compare against.
"""

from dataclasses import dataclass


def hallucination_rate(labels: list[bool]) -> float:
    """Fraction of examples whose response is unsupported by its context."""
    if not labels:
        return 0.0
    return sum(1 for x in labels if x) / len(labels)


@dataclass
class DetectionMetrics:
    """Verifier quality at detecting hallucinations (positive class = hallucinated)."""

    precision: float
    recall: float
    f1: float
    accuracy: float
    auroc: float | None  # None when scores not given or one class is absent
    tp: int
    fp: int
    tn: int
    fn: int
    n: int

    def __str__(self) -> str:
        a = f"{self.auroc:.3f}" if self.auroc is not None else "n/a"
        return (
            f"P={self.precision:.3f} R={self.recall:.3f} F1={self.f1:.3f} "
            f"Acc={self.accuracy:.3f} AUROC={a} "
            f"(tp={self.tp} fp={self.fp} tn={self.tn} fn={self.fn}, n={self.n})"
        )


def _auroc(y_true: list[bool], scores: list[float]) -> float | None:
    """AUROC via the rank (Mann-Whitney U) formula, with tie-averaged ranks.

    Computed by hand rather than pulled from sklearn so the calibration story
    is fully ownable: AUROC = P(score(positive) > score(negative)), i.e. the
    probability the verifier scores a real hallucination above a faithful one.
    """
    paired = sorted(zip(scores, y_true), key=lambda p: p[0])

    # Assign ranks 1..n, averaging ranks within tied score groups.
    ranks = [0.0] * len(paired)
    i = 0
    while i < len(paired):
        j = i
        while j < len(paired) and paired[j][0] == paired[i][0]:
            j += 1
        avg_rank = (i + 1 + j) / 2.0  # mean of 1-indexed ranks i+1 .. j
        for k in range(i, j):
            ranks[k] = avg_rank
        i = j

    n_pos = sum(1 for _, t in paired if t)
    n_neg = len(paired) - n_pos
    if n_pos == 0 or n_neg == 0:
        return None  # AUROC undefined when a class is absent

    sum_pos_ranks = sum(r for r, (_, t) in zip(ranks, paired) if t)
    return (sum_pos_ranks - n_pos * (n_pos + 1) / 2.0) / (n_pos * n_neg)


def detection_metrics(
    y_true: list[bool],
    y_pred: list[bool],
    scores: list[float] | None = None,
) -> DetectionMetrics:
    """Precision/recall/F1/accuracy (+ AUROC if `scores` given).

    y_true / y_pred / scores are aligned per example. `scores` is the verifier's
    continuous hallucination score (higher = more likely hallucinated) and is
    only needed for AUROC; P/R/F1 come from the thresholded `y_pred`.
    """
    if len(y_true) != len(y_pred):
        raise ValueError("y_true and y_pred must be the same length")

    tp = sum(1 for t, p in zip(y_true, y_pred) if t and p)
    fp = sum(1 for t, p in zip(y_true, y_pred) if not t and p)
    tn = sum(1 for t, p in zip(y_true, y_pred) if not t and not p)
    fn = sum(1 for t, p in zip(y_true, y_pred) if t and not p)

    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    accuracy = (tp + tn) / len(y_true) if y_true else 0.0
    auroc = _auroc(y_true, scores) if scores is not None else None

    return DetectionMetrics(precision, recall, f1, accuracy, auroc, tp, fp, tn, fn, len(y_true))
