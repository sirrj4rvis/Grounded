"""Phase 1 deliverable: the BASELINE hallucination measurement + the harness
that proves our labels map correctly.

This is the project's foundation. Before building any verifier we establish:
  (a) we can load real labelled benchmarks into one schema, and
  (b) the labels map correctly — checked two ways:
        * HaluEval QA must be exactly 50% hallucinated (balanced by design);
          any deviation means our mapping is wrong.
        * RAGTruth prevalence must vary sensibly by model (stronger models
          hallucinate less) — a sanity signal no off-by-one mapping would fake.

IMPORTANT framing (own this for the viva): RAGTruth's responses were generated
by other LLMs and human-annotated. The baseline number here is the GROUND-TRUTH
prevalence of unsupported responses in the benchmark. Our Grounded system is a
detector/corrector evaluated against these labels; we are NOT yet measuring our
own Phase-0 generator's hallucination rate (that needs labels we don't have).

Run:  python -m eval.baseline
"""

from collections import defaultdict

from eval.datasets import load_halueval_qa, load_ragtruth
from eval.metrics import hallucination_rate


def _group_rate(examples, key) -> dict[str, tuple[float, int]]:
    """Map each group -> (hallucination_rate, count), sorted by group name."""
    buckets: dict[str, list[bool]] = defaultdict(list)
    for ex in examples:
        buckets[key(ex)].append(ex.hallucinated)
    return {g: (hallucination_rate(v), len(v)) for g, v in sorted(buckets.items())}


def _print_rate_table(title: str, table: dict[str, tuple[float, int]]) -> None:
    print(f"  {title}")
    for group, (rate, n) in table.items():
        print(f"    {group:<28} {rate * 100:5.1f}%   (n={n})")


def main() -> None:
    print("Loading benchmarks (downloads once to data/benchmarks/) ...\n")

    # --- RAGTruth (primary) ---
    rt_all = load_ragtruth()
    rt_test = [e for e in rt_all if e.split == "test"]
    print(f"RAGTruth: {len(rt_all)} responses total | {len(rt_test)} in test split")
    print(f"  overall hallucination rate : {hallucination_rate([e.hallucinated for e in rt_all]) * 100:.1f}%")
    print(f"  TEST hallucination rate     : {hallucination_rate([e.hallucinated for e in rt_test]) * 100:.1f}%  <-- BASELINE")
    _print_rate_table("by task_type (test):", _group_rate(rt_test, lambda e: e.task_type))
    _print_rate_table("by model (test):", _group_rate(rt_test, lambda e: e.meta["model"]))

    # --- HaluEval QA (secondary, cross-dataset check) ---
    he = load_halueval_qa()
    he_rate = hallucination_rate([e.hallucinated for e in he])
    print(f"\nHaluEval QA: {len(he)} examples (1 faithful + 1 hallucinated per row)")
    print(f"  hallucination rate : {he_rate * 100:.1f}%  (must be 50.0% by construction)")

    # --- Go/No-Go: label-mapping correctness checks ---
    print("\n--- label-mapping checks ---")
    ok_balance = abs(he_rate - 0.5) < 1e-9
    print(f"  [{'PASS' if ok_balance else 'FAIL'}] HaluEval is exactly 50% hallucinated")

    by_model = _group_rate(rt_test, lambda e: e.meta["model"])
    gpt4 = next((r for m, (r, _) in by_model.items() if "gpt-4" in m.lower()), None)
    worst = max(r for r, _ in by_model.values())
    # Stronger model (GPT-4) should hallucinate less than the worst model.
    ok_order = gpt4 is not None and gpt4 < worst
    print(f"  [{'PASS' if ok_order else 'FAIL'}] GPT-4 hallucinates less than the worst model "
          f"({(gpt4 or 0) * 100:.1f}% < {worst * 100:.1f}%)")

    nonempty = 0 < hallucination_rate([e.hallucinated for e in rt_test]) < 1
    print(f"  [{'PASS' if nonempty else 'FAIL'}] RAGTruth test prevalence is in (0, 1)")

    print("\nGo/No-Go:", "GO — measurement is solid." if (ok_balance and ok_order and nonempty)
          else "NO-GO — investigate label mapping before proceeding.")


if __name__ == "__main__":
    main()
