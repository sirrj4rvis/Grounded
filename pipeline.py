"""Grounded end-to-end pipeline: retrieve -> generate -> verify -> correct.

This is the LIVE path (demo / API). The benchmark numbers come from
eval/run_eval.py, which applies the same corrector to RAGTruth's labelled
responses — same verification logic, different entry point.

Usage:
    from pipeline import Grounded
    g = Grounded()                       # mode="drop" | "flag" | "regenerate"
    report = g.ask("What is coral bleaching?")
"""

import json

from rag.generator import complete, generate
from rag.retriever import HybridRetriever
from verify.corrector import correct
from verify.nli import get_verifier

# Phase-2 calibrated sentence-level threshold (max-F1 on RAGTruth calibration
# split). Falls back to 0.5 if the calibration artifact isn't present.
def _calibrated_threshold(default: float = 0.5) -> float:
    try:
        return json.load(open("data/minicheck_sentence.json"))["threshold"]
    except (FileNotFoundError, KeyError, json.JSONDecodeError):
        return default


class Grounded:
    """The self-correcting RAG layer, wired together. Models load lazily."""

    def __init__(self, verifier_kind: str = "minicheck", threshold: float | None = None,
                 top_k: int = 4, mode: str = "drop", max_iters: int = 2):
        self.threshold = threshold if threshold is not None else _calibrated_threshold()
        self.top_k = top_k
        self.mode = mode
        self.max_iters = max_iters
        self._verifier_kind = verifier_kind
        self._retriever = None
        self._verifier = None

    @property
    def retriever(self):
        if self._retriever is None:
            self._retriever = HybridRetriever()
        return self._retriever

    @property
    def verifier(self):
        if self._verifier is None:
            self._verifier = get_verifier(self._verifier_kind)
        return self._verifier

    def ask(self, query: str) -> dict:
        """Full pipeline. Returns the answer plus per-sentence receipts."""
        chunks = self.retriever.retrieve(query, top_k=self.top_k)
        answer = generate(query, chunks)

        # The verification context is exactly what the generator saw.
        context = "\n\n".join(c["text"] for c in chunks)

        def regenerate_fn(supported: list[str]) -> str:
            # Rewrite from the supported sentences ONLY — the model may rephrase
            # but gets no license to reintroduce unsupported content.
            facts = "\n".join(f"- {s}" for s in supported)
            return complete(
                f"Question: {query}\n\nVerified facts:\n{facts}\n\n"
                "Rewrite a concise answer to the question using ONLY the verified "
                "facts above. Do not add any information not in the facts.",
            )

        result = correct(
            self.verifier, context, answer, self.threshold,
            mode=self.mode, max_iters=self.max_iters,
            regenerate_fn=regenerate_fn if self.mode == "regenerate" else None,
        )

        return {
            "query": query,
            "answer": result.original,
            "corrected": result.corrected,
            "groundedness": result.groundedness,
            "abstained": result.abstained,
            "threshold": result.threshold,
            "iterations": result.iterations,
            "claims": [
                {"text": v.text, "support": round(v.support, 3), "supported": v.kept,
                 "evidence": v.evidence}
                for v in result.verdicts
            ],
            "sources": [{"id": c["id"], "source": c["source"]} for c in chunks],
        }


if __name__ == "__main__":
    import sys

    g = Grounded()
    out = g.ask(sys.argv[1] if len(sys.argv) > 1 else "What is coral bleaching?")
    print(json.dumps(out, indent=2))
