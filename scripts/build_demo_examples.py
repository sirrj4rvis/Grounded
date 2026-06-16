"""Precompute a few REAL RAGTruth examples (with verifier verdicts) for the
dashboard's "Examples" view, so the green/red catch can be shown in the browser
without waiting on (or fighting) the live generator.

Each example is written in the SAME shape as the /ask response, so the dashboard
renders it with the exact same claim-by-claim code path.

Run:  python scripts/build_demo_examples.py
"""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from eval.datasets import load_ragtruth
from eval.run_eval import overlaps
from verify.decompose import split_sentences_with_offsets
from verify.nli import get_verifier

OUT = Path("dashboard/demo_examples.json")
THRESHOLD = 0.77  # match the dashboard's live threshold label


def extract_question(prompt: str) -> str:
    """Pull a readable question out of a RAGTruth QA prompt; fallback gracefully."""
    m = re.search(r"question:\s*(.+?)(?:\n|answer:|$)", prompt or "", re.IGNORECASE | re.DOTALL)
    if m:
        return m.group(1).strip()[:160]
    return "(real RAGTruth QA response)"


def pick(examples, n=3):
    picked = []
    for e in examples:
        if e.task_type != "QA" or not e.hallucinated:
            continue
        sents = split_sentences_with_offsets(e.response)
        if len(sents) < 3:
            continue
        spans = [(s["start"], s["end"]) for s in e.spans]
        bad = [any(overlaps(a, b, sa, sb) for sa, sb in spans) for _, a, b in sents]
        if any(bad) and not all(bad):
            picked.append((e, sents, bad))
        if len(picked) >= n:
            break
    return picked


def main():
    print("Loading RAGTruth + MiniCheck verifier...")
    examples = load_ragtruth(split="test")
    verifier = get_verifier("minicheck")

    out = []
    for e, sents, bad in pick(examples):
        texts = [s for s, _, _ in sents]
        scored = verifier.support_scores_multi(e.context, texts, return_evidence=True)
        claims = [
            {"text": t, "support": round(p, 3), "supported": p >= THRESHOLD,
             "gt_hallucination": b, "evidence": ev}
            for t, (p, ev), b in zip(texts, scored, bad)
        ]
        kept = [c["text"] for c in claims if c["supported"]]
        out.append({
            "query": extract_question(e.meta.get("prompt", "")),
            "answer": e.response,
            "corrected": " ".join(kept) if kept else "I can't answer this from the provided context.",
            "groundedness": sum(c["supported"] for c in claims) / len(claims),
            "abstained": not kept,
            "threshold": THRESHOLD,
            "claims": claims,
            "sources": [{"id": e.id, "source": f"RAGTruth/{e.meta['model']}"}],
            "note": "Real RAGTruth response. Red = human-labeled hallucination caught by the verifier.",
        })
        print(f"  added {e.id} ({e.meta['model']}): {len(claims)} claims, "
              f"{sum(c['supported'] for c in claims)} kept")

    OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"Wrote {len(out)} examples to {OUT}")


if __name__ == "__main__":
    main()
