"""Generate report/poster figures from the dumped eval JSONs. No model needed.

Produces (into figures/):
  1. tradeoff.png       — hallucination reduction vs clean retention across
                          thresholds (the headline trade-off curve).
  2. before_after.png   — baseline vs corrected hallucination rate at the
                          recommended operating point, with 95% CIs.
  3. verifier_ablation.png — MiniCheck vs DeBERTa-NLI AUROC, RAGTruth + HaluEval.
  4. score_separation.png  — verifier support-score distribution for clean vs
                          hallucinated sentences (why it works).

Run:  python -m eval.figures
"""

import json
import random
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # headless: write files, never open a window
import matplotlib.pyplot as plt

OUT = Path("figures")
GREEN, RED, BLUE, GREY = "#1a7f37", "#b42318", "#1f6feb", "#6b7280"


def _load(path):
    return json.load(open(path, encoding="utf-8"))


def fig_tradeoff(full):
    sweep = full["sweep"]
    red = [(s["rate_before"] - s["rate_after"]) / s["rate_before"] * 100 for s in sweep]
    keep = [s["clean_retention"] * 100 for s in sweep]
    thr = [s["threshold"] for s in sweep]
    fig, ax = plt.subplots(figsize=(6, 4.5))
    ax.plot(keep, red, "-o", color=BLUE, lw=2)
    for k, r, t in zip(keep, red, thr):
        ax.annotate(f"thr={t:g}", (k, r), textcoords="offset points", xytext=(6, -10), fontsize=8, color=GREY)
    ax.set_xlabel("Clean content retained (%)")
    ax.set_ylabel("Hallucination reduction (%)")
    ax.set_title("Grounded: reduction vs. content-preservation trade-off\nRAGTruth test (n=2700)")
    ax.grid(alpha=0.3)
    ax.invert_xaxis()  # left = aggressive (less kept), right = conservative
    fig.tight_layout()
    fig.savefig(OUT / "tradeoff.png", dpi=150)
    plt.close(fig)


def fig_before_after(full):
    # recommended operating point = thr 0.25 row
    row = min(full["sweep"], key=lambda s: abs(s["threshold"] - 0.25))
    examples = full["examples"]
    thr = row["threshold"]
    # bootstrap CIs for before/after
    rng = random.Random(0)
    bs_b, bs_a = [], []
    n = len(examples)
    for _ in range(2000):
        samp = [examples[rng.randrange(n)] for _ in range(n)]
        bs_b.append(sum(e["hallucinated"] for e in samp) / n * 100)
        bs_a.append(sum(any(s["gt_bad"] for s in e["sentences"] if s["support"] >= thr)
                        for e in samp) / n * 100)
    def ci(v):
        v = sorted(v)
        return v[int(0.025 * len(v))], v[int(0.975 * len(v))]
    b, a = row["rate_before"] * 100, row["rate_after"] * 100
    bl, bh = ci(bs_b)
    al, ah = ci(bs_a)
    fig, ax = plt.subplots(figsize=(4.5, 4.5))
    ax.bar([0, 1], [b, a], color=[RED, GREEN], width=0.6,
           yerr=[[b - bl, a - al], [bh - b, ah - a]], capsize=8)
    ax.set_xticks([0, 1])
    ax.set_xticklabels(["Baseline RAG", f"Grounded\n(thr={thr:g})"])
    ax.set_ylabel("Hallucination rate (%)")
    ax.set_title("Hallucination rate, baseline vs. Grounded\n(95% CI, n=2700)")
    for x, v in [(0, b), (1, a)]:
        ax.text(x, v + 1, f"{v:.1f}%", ha="center", fontweight="bold")
    ax.set_ylim(0, max(bh, b) * 1.25)
    fig.tight_layout()
    fig.savefig(OUT / "before_after.png", dpi=150)
    plt.close(fig)


def fig_ablation():
    rt = {"MiniCheck": 0.854, "DeBERTa-NLI": 0.778}  # RAGTruth test AUROC (Phase 2/4)
    he = {"MiniCheck": _load("data/halueval_minicheck.json")["auroc"],
          "DeBERTa-NLI": _load("data/halueval_deberta.json")["auroc"]}
    models = ["MiniCheck", "DeBERTa-NLI"]
    x = range(len(models))
    fig, ax = plt.subplots(figsize=(5.5, 4.5))
    ax.bar([i - 0.2 for i in x], [rt[m] for m in models], 0.4, label="RAGTruth", color=BLUE)
    ax.bar([i + 0.2 for i in x], [he[m] for m in models], 0.4, label="HaluEval (transfer)", color=GREEN)
    ax.set_xticks(list(x))
    ax.set_xticklabels(models)
    ax.set_ylabel("AUROC (hallucination detection)")
    ax.set_title("Verifier ablation: MiniCheck vs. generic NLI")
    ax.set_ylim(0.5, 1.0)
    ax.axhline(0.5, color=GREY, ls="--", lw=1, label="chance")
    ax.legend()
    for i, m in enumerate(models):
        ax.text(i - 0.2, rt[m] + 0.01, f"{rt[m]:.2f}", ha="center", fontsize=9)
        ax.text(i + 0.2, he[m] + 0.01, f"{he[m]:.2f}", ha="center", fontsize=9)
    fig.tight_layout()
    fig.savefig(OUT / "verifier_ablation.png", dpi=150)
    plt.close(fig)


def fig_score_separation(full):
    clean, bad = [], []
    for e in full["examples"]:
        for s in e["sentences"]:
            (bad if s["gt_bad"] else clean).append(s["support"])
    fig, ax = plt.subplots(figsize=(6, 4.5))
    bins = [i / 20 for i in range(21)]
    ax.hist(clean, bins=bins, density=True, alpha=0.6, color=GREEN, label=f"grounded sentences (n={len(clean)})")
    ax.hist(bad, bins=bins, density=True, alpha=0.6, color=RED, label=f"hallucinated sentences (n={len(bad)})")
    ax.set_xlabel("MiniCheck support score")
    ax.set_ylabel("density")
    ax.set_title("Why it works: verifier separates grounded from\nhallucinated sentences (RAGTruth test)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUT / "score_separation.png", dpi=150)
    plt.close(fig)


def main():
    OUT.mkdir(exist_ok=True)
    full = _load("data/correction_eval_full.json")
    fig_tradeoff(full)
    fig_before_after(full)
    fig_ablation()
    fig_score_separation(full)
    print(f"Wrote 4 figures to {OUT}/")


if __name__ == "__main__":
    main()
