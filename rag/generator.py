"""Generator: answer a query from retrieved chunks via Ollama (CPU mode).

Talks to the local Ollama HTTP API directly with `requests` — no client
library, so the exact prompt and parameters are visible and explainable.
The prompt instructs the model to answer ONLY from the provided context;
that constraint is the behaviour the whole project measures, so it lives
here in one obvious place.
"""

import os

import requests

# Configurable so the API can point at an Ollama running elsewhere (e.g. the
# Docker host). Default to 127.0.0.1 (not "localhost"): on Windows "localhost"
# resolves to IPv6 ::1 first, which can hit a different Ollama instance than the
# IPv4 one the model was pulled into.
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")
GEN_MODEL = os.environ.get("GROUNDED_GEN_MODEL", "qwen2.5:3b-instruct")

# CPU generation is slow (~3-8 tok/s); give it room before timing out.
TIMEOUT_SECONDS = 600

SYSTEM_PROMPT = (
    "You are a careful assistant. Answer the question using ONLY the provided "
    "context passages. Do not use outside knowledge. If the context does not "
    "contain the answer, reply exactly: \"I don't know based on the provided "
    "context.\" Keep the answer concise."
)


def build_prompt(query: str, chunks: list[dict]) -> str:
    """Format retrieved chunks + question into a single user prompt.

    Chunks are labelled [1], [2], ... so later phases can ask the model to
    cite which passage supports each statement.
    """
    context = "\n\n".join(f"[{i + 1}] {c['text']}" for i, c in enumerate(chunks))
    return f"Context passages:\n{context}\n\nQuestion: {query}\n\nAnswer:"


def complete(prompt: str, system: str = "", model: str = GEN_MODEL, temperature: float = 0.0) -> str:
    """Single-turn completion via Ollama. The one place we talk to the model.

    Shared by the RAG generator and the claim decomposer so there's exactly one
    Ollama client, one timeout, and one default temperature in the codebase.
    """
    response = requests.post(
        f"{OLLAMA_URL}/api/generate",
        json={
            "model": model,
            "system": system,
            "prompt": prompt,
            "stream": False,
            # temperature 0 by default: eval needs reproducible output, and we
            # measure groundedness, not creativity.
            "options": {"temperature": temperature},
        },
        timeout=TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    return response.json()["response"].strip()


def generate(query: str, chunks: list[dict], model: str = GEN_MODEL) -> str:
    """Return the model's answer for (query, chunks). Raises on Ollama errors."""
    return complete(build_prompt(query, chunks), system=SYSTEM_PROMPT, model=model)
