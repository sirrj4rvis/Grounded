"""Phase 4: answer-quality preservation via a blind LLM judge.

Clean-sentence retention counts WHAT survived correction; it can't say whether
what survived still ANSWERS the question. This script asks a local LLM judge to
compare original vs corrected answers for completeness/helpfulness, blind:

  - Only examples where correction actually CHANGED the answer are judged
    (unchanged answers are trivially quality-preserving).
  - The two answers are shown as A/B in seeded-random order so the judge can't
    learn that "B is always the corrected one".
  - Verdict per example: which answer addresses the task better — A, B, or TIE.
    We then map back to original/corrected and report the distribution.

The judge is qwen2.5:3b via Ollama — the same class of model as the generator.
A 3B judge is noisy per-example; we only read the AGGREGATE distribution, state
that openly, and treat "corrected not much worse than original" as the success
criterion (correction removes content, so the question is how much utility it
costs, not whether it adds any).

Run:  python -m eval.quality_judge --threshold 0.25 --max-examples 30
"""

import argparse
import json
import random

from rag.generator import complete

JUDGE_SYSTEM = (
    "You are an impartial judge. Compare two answers to the same task and "
    "decide which one is more complete and helpful for the user. Consider only "
    "helpfulness and completeness, not style. Reply with EXACTLY one word: "
    "A, B, or TIE."
)


def judge_pair(task_prompt: str, answer_a: str, answer_b: str) -> str:
    """One blind comparison. Returns 'A' | 'B' | 'TIE' (defensive parse)."""
    prompt = (
        f"Task given to an assistant:\n{task_prompt[:1500]}\n\n"
        f"Answer A:\n{answer_a}\n\nAnswer B:\n{answer_b}\n\n"
        "Which answer is more complete and helpful? Reply A, B, or TIE."
    )
    raw = complete(prompt, system=JUDGE_SYSTEM).strip().upper()
    for token in ("TIE", "A", "B"):  # TIE first: "A TIE" should parse as TIE
        if token in raw.split() or raw == token:
            return token
    return "TIE"  # unparseable -> count as tie rather than invent a winner


def corrected_answer(sentences: list[dict], threshold: float) -> tuple[str, bool]:
    """Rebuild the drop-corrected answer from dumped per-sentence scores."""
    kept = [s["text"] for s in sentences if s["support"] >= threshold]
    if not kept:
        return "I can't answer this from the provided context.", True
    return " ".join(kept), False


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default="data/correction_eval.json")
    ap.add_argument("--threshold", type=float, default=0.25)
    ap.add_argument("--max-examples", type=int, default=30)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    d = json.load(open(args.json, encoding="utf-8"))
    rng = random.Random(args.seed)

    # The eval dump doesn't carry the original task prompt; join it back from
    # RAGTruth by id so the judge sees the actual question/instruction.
    from eval.datasets import load_ragtruth

    prompt_by_id = {e.id: e.meta.get("prompt") or "" for e in load_ragtruth(split="test")}

    # The dump stores sentences; the original answer is their concatenation.
    # Judge only examples the corrector actually changed, and skip abstentions
    # (an abstained answer is a known total quality loss; it's reported as the
    # abstention rate, not smuggled into the judge stats).
    candidates = []
    for ex in d["examples"]:
        original = " ".join(s["text"] for s in ex["sentences"])
        corrected, abstained = corrected_answer(ex["sentences"], args.threshold)
        if corrected != original and not abstained:
            candidates.append((ex, original, corrected))
    rng.shuffle(candidates)
    candidates = candidates[: args.max_examples]
    print(f"Judging {len(candidates)} changed (non-abstained) answers at thr={args.threshold}")

    wins = {"original": 0, "corrected": 0, "tie": 0}
    records = []
    for i, (ex, original, corrected) in enumerate(candidates, 1):
        flip = rng.random() < 0.5  # blind order
        a, b = (corrected, original) if flip else (original, corrected)
        task_prompt = prompt_by_id.get(ex["id"]) or f"({ex['task']} task) Answer from the given context."
        verdict = judge_pair(task_prompt, a, b)
        winner = ("corrected" if (verdict == "A") == flip else "original") if verdict != "TIE" else "tie"
        wins[winner] += 1
        records.append({"id": ex["id"], "verdict": verdict, "winner": winner})
        print(f"    [{i}/{len(candidates)}] {ex['id']}: {winner}", flush=True)

    n = max(1, len(candidates))
    print("\n" + "=" * 56)
    print(f"BLIND LLM-JUDGE — original vs drop-corrected (thr={args.threshold})")
    print(f"  original better : {wins['original']:>3}  ({wins['original'] / n * 100:.0f}%)")
    print(f"  corrected better: {wins['corrected']:>3}  ({wins['corrected'] / n * 100:.0f}%)")
    print(f"  tie             : {wins['tie']:>3}  ({wins['tie'] / n * 100:.0f}%)")
    print("=" * 56)

    if args.out:
        json.dump({"threshold": args.threshold, "n": len(candidates),
                   "wins": wins, "records": records},
                  open(args.out, "w", encoding="utf-8"), indent=2)
        print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()
