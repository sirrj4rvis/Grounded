"""The verifier: score how well a CLAIM is supported by a CONTEXT.

Two interchangeable verifiers behind one interface:
  MiniCheckVerifier   (primary)  — lytang/MiniCheck-DeBERTa-v3-Large, a model
                                   purpose-built for "is this claim grounded in
                                   this document". Binary head; support = P(1).
  DebertaNLIVerifier  (baseline) — MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli,
                                   a generic NLI model; support = P(entailment).
Comparing the two is the clean ablation the project reports.

Every verifier returns a SUPPORT SCORE in [0, 1]: higher = better grounded.
A hallucination is then predicted when support < threshold (calibrated later in
eval/calibrate.py). We score support, not "hallucination", so the model output
maps directly onto the NLI notion of entailment.

THE LONG-CONTEXT PROBLEM (the load-bearing detail here):
RAGTruth Summary/Data2txt contexts routinely exceed the 512-token limit of
these encoders. If we just truncate, a claim supported by the tail of a long
document looks UNsupported -> a false hallucination. So we split the context
into overlapping token windows that fit the model and take the MAX support over
windows: a claim is grounded if ANY part of the context supports it. This is the
MiniCheck chunking strategy and it is essential for honest scores on long inputs.
"""

import os
from abc import ABC, abstractmethod

import torch
import torch.nn.functional as F
from transformers import AutoModelForSequenceClassification, AutoTokenizer

# CPU-only: use the cores we have. Set once at import.
torch.set_num_threads(max(1, (os.cpu_count() or 4)))


def _maybe_lower_priority() -> None:
    """Drop to BELOW_NORMAL priority when GROUNDED_LOW_PRIORITY=1 (Windows).

    Used for long offline runs so the foreground (browser, editor) always wins
    the CPU: the eval soaks up only idle cycles. No effect on the live demo or
    normal eval runs, which leave the env var unset and stay at normal priority.
    """
    if os.environ.get("GROUNDED_LOW_PRIORITY") != "1":
        return
    try:
        import ctypes  # BELOW_NORMAL_PRIORITY_CLASS = 0x00004000

        k32 = ctypes.windll.kernel32
        k32.SetPriorityClass(k32.GetCurrentProcess(), 0x00004000)
    except Exception:
        pass  # non-Windows or API unavailable: priority just stays normal


_maybe_lower_priority()

MAX_LENGTH = 512  # encoder limit for both DeBERTa models
WINDOW_OVERLAP = 50  # token overlap between context windows, so claims that
#                      straddle a window boundary stay scorable from one side
BATCH_SIZE = 16  # (window, claim) pairs scored per forward pass


class Verifier(ABC):
    """Common interface: (context, claim) -> support score in [0, 1]."""

    name: str

    def __init__(self, model_name: str):
        self.model_name = model_name
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForSequenceClassification.from_pretrained(model_name)
        self.model.eval()

    @abstractmethod
    def _support_index(self) -> int:
        """Which logit column means 'claim is supported by context'."""

    def _context_windows(self, context: str, claim_token_len: int) -> list[str]:
        """Split context into windows that leave room for the claim.

        Budget = MAX_LENGTH - claim tokens - special tokens. We tokenize the
        context once, slice it into overlapping windows of that budget, and
        decode each back to text so the pair can be re-encoded normally.
        """
        ctx_ids = self.tokenizer(context, add_special_tokens=False)["input_ids"]
        budget = max(64, MAX_LENGTH - claim_token_len - 4)
        if len(ctx_ids) <= budget:
            return [context]

        windows = []
        step = max(1, budget - WINDOW_OVERLAP)
        for start in range(0, len(ctx_ids), step):
            chunk = ctx_ids[start : start + budget]
            # Stop once the tail is just overlap already covered by the prior window.
            if len(chunk) <= WINDOW_OVERLAP and windows:
                break
            windows.append(self.tokenizer.decode(chunk, skip_special_tokens=True))
        return windows

    def support_score(self, context: str, claim: str) -> float:
        """Max support for `claim` across context windows. Higher = grounded."""
        return self.support_scores_multi(context, [claim])[0]

    def support_scores_multi(self, context: str, claims: list[str], return_evidence: bool = False):
        """Support for EACH claim against the SAME context, in batched passes.

        The hot path for claim-level verification: a response with S sentences
        and a context that splits into W windows is S*W (window, claim) pairs.
        The old code ran one forward pass per claim; here we build all S*W pairs
        and push them through in batches of BATCH_SIZE, so a long Data2txt
        response is a handful of large matmuls instead of a Python loop of small
        ones. Per claim we still take the MAX over its windows (grounded if ANY
        window supports it). Scores are identical to the per-claim version — only
        the batching changes.

        Windows are sized for the LONGEST claim so every (window, claim) pair
        fits in MAX_LENGTH without truncating away claim text.

        return_evidence=True additionally returns, per claim, the context window
        that produced the max score (the closest-matching passage). This only
        EXPOSES information the scoring already computes — the score itself is
        unchanged — so the verification logic is untouched.
        """
        if not claims:
            return []
        idx = self._support_index()
        max_claim_len = max(
            len(self.tokenizer(c, add_special_tokens=False)["input_ids"]) for c in claims
        )
        windows = self._context_windows(context, max_claim_len)
        w_count = len(windows)

        # Flatten to (window, claim) pairs, remembering which claim each belongs to.
        flat_windows, flat_claims, owner = [], [], []
        for ci, claim in enumerate(claims):
            for w in windows:
                flat_windows.append(w)
                flat_claims.append(claim)
                owner.append(ci)

        best = [0.0] * len(claims)
        best_win = [0] * len(claims)  # which window index gave each claim's max
        for start in range(0, len(flat_windows), BATCH_SIZE):
            enc = self.tokenizer(
                flat_windows[start : start + BATCH_SIZE],
                flat_claims[start : start + BATCH_SIZE],
                return_tensors="pt",
                truncation=True,
                max_length=MAX_LENGTH,
                padding=True,
            )
            with torch.no_grad():
                probs = F.softmax(self.model(**enc).logits, dim=-1)[:, idx]
            for k, p in enumerate(probs):
                j = start + k
                ci = owner[j]
                score = float(p)
                if score >= best[ci]:
                    best[ci] = score
                    best_win[ci] = j % w_count  # flat layout is contiguous per claim
        if return_evidence:
            return [(best[ci], windows[best_win[ci]]) for ci in range(len(claims))]
        return best

    def support_scores(self, pairs: list[tuple[str, str]]) -> list[float]:
        """Score many (context, claim) pairs. Plain loop — fine for offline eval."""
        return [self.support_score(ctx, claim) for ctx, claim in pairs]


class MiniCheckVerifier(Verifier):
    """Primary verifier — purpose-built grounding checker (binary head)."""

    name = "minicheck"

    def __init__(self, model_name: str = "lytang/MiniCheck-DeBERTa-v3-Large"):
        super().__init__(model_name)

    def _support_index(self) -> int:
        # Binary head: label 1 == supported (verified empirically on known pairs).
        return 1


class DebertaNLIVerifier(Verifier):
    """Baseline verifier — generic 3-way NLI; support = P(entailment)."""

    name = "deberta-nli"

    def __init__(self, model_name: str = "MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli"):
        super().__init__(model_name)

    def _support_index(self) -> int:
        # Resolve 'entailment' from the model's own label map rather than
        # hard-coding 0, so a relabelled checkpoint can't silently flip support.
        for i, label in self.model.config.id2label.items():
            if label.lower() == "entailment":
                return int(i)
        raise ValueError(f"no 'entailment' label in {self.model.config.id2label}")


def get_verifier(kind: str = "minicheck") -> Verifier:
    """Factory: 'minicheck' (primary) or 'deberta-nli' (baseline)."""
    if kind == "minicheck":
        return MiniCheckVerifier()
    if kind == "deberta-nli":
        return DebertaNLIVerifier()
    raise ValueError(f"unknown verifier {kind!r}")
