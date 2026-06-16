"""Self-correction: verify each sentence of an answer, then DROP / FLAG /
REGENERATE the unsupported ones.

The contract (own this for the viva):
  - The verifier gives each sentence a support score in [0, 1] w.r.t. the
    retrieved context. support < threshold => treated as unsupported.
  - mode="drop"       : remove unsupported sentences; keep the rest verbatim.
                        Deterministic and cheap — this is what the benchmark
                        eval uses, because its effect is exactly measurable
                        against RAGTruth's span labels.
  - mode="flag"       : change nothing; just report per-sentence verdicts
                        (the dashboard's green/red view).
  - mode="regenerate" : ask the generator to rewrite the answer using ONLY the
                        supported sentences as source material, re-verify, and
                        repeat up to max_iters (Chain-of-Verification style).
                        Falls back to dropping whatever is still unsupported
                        after the last iteration, so the loop ALWAYS terminates
                        with a fully-supported (or abstained) answer.
  - If nothing survives, we ABSTAIN rather than return an empty string —
    an honest "can't answer from the context" beats a fabricated answer.

Correction can only remove/replace content, never invent it — that is the
safety property that makes "hallucination rate goes down" trustworthy. The
price (dropping correct content too) is measured explicitly in eval/run_eval.py
as clean-sentence retention, never assumed away.
"""

from dataclasses import dataclass, field

from verify.decompose import split_sentences

ABSTAIN_MESSAGE = "I can't answer this from the provided context."


@dataclass
class SentenceVerdict:
    """One sentence of the answer with its verifier verdict."""

    text: str
    support: float
    kept: bool
    evidence: str = ""  # the context window that best supports/contradicts it


@dataclass
class CorrectionResult:
    """Everything downstream consumers need: the corrected answer + receipts."""

    original: str
    corrected: str
    verdicts: list[SentenceVerdict] = field(default_factory=list)
    threshold: float = 0.5
    abstained: bool = False
    iterations: int = 1  # >1 only in regenerate mode

    @property
    def groundedness(self) -> float:
        """Fraction of the ORIGINAL answer's sentences that were supported.

        A property of the answer as generated (pre-correction), so it is
        comparable across modes — drop/regenerate change the output, not
        this score.
        """
        if not self.verdicts:
            return 0.0
        return sum(1 for v in self.verdicts if v.kept) / len(self.verdicts)


def _verify_sentences(verifier, context: str, sentences: list[str], threshold: float):
    """Score each sentence; kept <=> support >= threshold. Captures evidence."""
    scored = verifier.support_scores_multi(context, sentences, return_evidence=True)
    return [
        SentenceVerdict(text=s, support=p, kept=p >= threshold, evidence=ev)
        for s, (p, ev) in zip(sentences, scored)
    ]


def correct(
    verifier,
    context: str,
    response: str,
    threshold: float,
    mode: str = "drop",
    max_iters: int = 2,
    regenerate_fn=None,
) -> CorrectionResult:
    """Verify `response` sentence-by-sentence and correct it.

    regenerate_fn(supported_sentences: list[str]) -> str is only needed for
    mode="regenerate"; the pipeline passes a closure that knows the original
    question, so the corrector stays generator-agnostic.
    """
    sentences = split_sentences(response)
    if not sentences:
        return CorrectionResult(original=response, corrected=ABSTAIN_MESSAGE,
                                threshold=threshold, abstained=True)

    verdicts = _verify_sentences(verifier, context, sentences, threshold)
    result = CorrectionResult(original=response, corrected=response,
                              verdicts=verdicts, threshold=threshold)

    if mode == "flag":
        return result  # report only; answer untouched

    if mode == "regenerate":
        if regenerate_fn is None:
            raise ValueError("mode='regenerate' requires regenerate_fn")
        current = verdicts
        for it in range(2, max_iters + 1):
            if all(v.kept for v in current):
                break  # nothing left to fix
            supported = [v.text for v in current if v.kept]
            if not supported:
                break  # nothing grounded to rewrite from -> fall through to drop
            rewritten = regenerate_fn(supported)
            current = _verify_sentences(verifier, context, split_sentences(rewritten), threshold)
            result.iterations = it
        # NOTE: result.verdicts stays = the ORIGINAL answer's verdicts (that is
        # what groundedness reports); the rewritten sentences live in `current`.
        verdicts_final = current
    else:  # drop
        verdicts_final = verdicts

    kept = [v.text for v in verdicts_final if v.kept]
    if kept:
        result.corrected = " ".join(kept)
    else:
        result.corrected = ABSTAIN_MESSAGE
        result.abstained = True
    return result
