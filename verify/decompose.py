"""Decompose an answer into ATOMIC CLAIMS — single verifiable statements.

This is the FActScore idea (Min et al. 2023): instead of judging a whole answer
as grounded/not, break it into the smallest independently-checkable factual
units and verify each one. Claim-level verification both localises WHERE an
answer is unsupported and lets the corrector drop/fix only the bad parts.

This is the squishy part of the project (the plan says so). The two failure
modes to watch, both visible by eye on a sample:
  - Under/over-decomposition: one claim smuggling several facts, or trivial
    fragments that aren't really verifiable.
  - Lost context: a claim like "He died in 1945" that dropped its subject and
    can't be verified standalone. The prompt explicitly asks the model to
    DECONTEXTUALISE — resolve pronouns/references so each claim stands alone.

We use the same local Ollama model as the generator. Whole-answer verification
(verify/nli.py over the full response) remains the coarse baseline; decomposition
is the improvement we ablate against it.
"""

import re

from rag.generator import complete

# --- Coarse method: deterministic sentence splitting -------------------------
# Free, reproducible, no model. Used as the fast decomposition baseline and as
# the fallback when LLM decomposition returns nothing.
#
# Splitting prose with a regex is inherently approximate; the goal is to avoid
# the false splits that produce junk fragments ("Dr.", "7."), because a fragment
# scores as unsupported and — since the response takes its MIN unit support —
# would falsely flag the whole answer. Three guards do most of the work:
#   * don't split after a single capital + period   -> "U.S.", "J. R. R."
#   * don't split after a known abbreviation+period  -> "Dr.", "Mr.", "etc."
#   * only split when the next sentence starts with a capital (optionally
#     quoted) -> kills "Feb. 7" and "version 3.1 of" style splits.
# Periods are included IN the abbreviation lookbehinds; the previous version
# omitted them, so the guards never fired. The LLM method handles the residual
# hard cases when fidelity matters.
_SENT_BOUNDARY = re.compile(
    r"(?<![A-Z]\.)"  # not a single capital initial (U.S., J.)
    r"(?<!Dr\.)(?<!Mr\.)(?<!Mrs\.)(?<!Ms\.)(?<!vs\.)(?<!etc\.)(?<!No\.)(?<!St\.)(?<!Fig\.)"
    r"(?<=[.!?])\s+"  # sentence-ending punctuation followed by whitespace
    r"(?=[\"'(\[]?[A-Z])"  # next sentence opens with a capital (maybe quoted)
)


def split_sentences(text: str) -> list[str]:
    """Split text into sentences. Coarse, deterministic, and fast (no model)."""
    text = text.strip()
    if not text:
        return []
    return [p.strip() for p in _SENT_BOUNDARY.split(text) if p.strip()]


def split_sentences_with_offsets(text: str) -> list[tuple[str, int, int]]:
    """split_sentences plus each sentence's (start, end) char offsets in `text`.

    Needed to align sentences with RAGTruth's character-span hallucination
    labels. Sentences are contiguous substrings of the original (the splitter
    only consumes whitespace), so a forward-moving find() recovers offsets
    exactly; the cursor guarantees a repeated sentence maps to its own
    occurrence, not an earlier copy.
    """
    out = []
    cursor = 0
    for sent in split_sentences(text):
        start = text.find(sent, cursor)
        if start < 0:  # defensive: should not happen, but never misalign silently
            start = text.find(sent)
        out.append((sent, start, start + len(sent)))
        cursor = start + len(sent)
    return out


DECOMPOSE_SYSTEM = (
    "You break text into atomic factual claims. A claim is a single, "
    "self-contained, verifiable statement. Follow these rules strictly:\n"
    "1. Each claim states exactly ONE fact.\n"
    "2. Make each claim stand alone: replace pronouns and references (he, it, "
    "this, the company) with the explicit entity they refer to.\n"
    "3. Only use information present in the text. Do NOT add, infer, or "
    "embellish.\n"
    "4. Ignore questions, opinions, and filler; extract only factual assertions.\n"
    "Output ONLY the claims, one per line, with no numbering or bullets."
)


def _parse_claims(raw: str) -> list[str]:
    """Turn the model's line-per-claim output into a clean list.

    Forgiving on purpose: small models drift into numbering ("1."), bullets
    ("- ", "* "), or stray blank lines even when told not to, so we strip those
    rather than trust perfect formatting.
    """
    claims = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        # Strip a leading "1.", "1)", "-", "*", "•" if the model added one.
        line = re.sub(r"^\s*(?:\d+[.)]|[-*•])\s*", "", line).strip()
        if line:
            claims.append(line)
    return claims


def decompose(answer: str, model: str | None = None) -> list[str]:
    """Answer -> list of atomic, decontextualised claims.

    Returns [answer] unchanged if the model emits nothing parseable, so the
    pipeline degrades to whole-answer verification rather than silently
    dropping the answer.
    """
    answer = answer.strip()
    if not answer:
        return []

    prompt = f"Break the following text into atomic claims:\n\n{answer}"
    raw = complete(prompt, system=DECOMPOSE_SYSTEM, model=model or _default_model())
    claims = _parse_claims(raw)
    return claims or [answer]


def _default_model() -> str:
    """Late import keeps the Ollama model name defined in one place."""
    from rag.generator import GEN_MODEL

    return GEN_MODEL
