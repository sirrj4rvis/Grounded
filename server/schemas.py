"""Pydantic schemas for the Grounded API — mirrors pipeline.Grounded.ask()."""

from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    # Caps keep a CPU box safe from runaway requests; None = server defaults.
    top_k: int | None = Field(None, ge=1, le=10)
    mode: str | None = Field(None, pattern="^(drop|flag|regenerate)$")


class Claim(BaseModel):
    text: str
    support: float
    supported: bool
    evidence: str = ""  # context window that best supports/contradicts the claim


class Source(BaseModel):
    id: str
    source: str


class AskResponse(BaseModel):
    query: str
    answer: str  # the raw generated answer (pre-correction)
    corrected: str  # the post-correction answer shown to the user
    groundedness: float  # fraction of original sentences supported
    abstained: bool
    threshold: float
    iterations: int
    claims: list[Claim]
    sources: list[Source]
    note: str = ""  # abstain reason / provenance (e.g. out-of-corpus); "" when absent
