"""End-to-end vanilla RAG: ingest (if needed) -> retrieve -> generate.

Usage (from the repo root, with Ollama running):
    python scripts/ask.py "What did the Antikythera mechanism predict?"
    python scripts/ask.py --reingest "..."   # force a corpus rebuild
"""

import argparse
import sys
from pathlib import Path

# Make `rag` importable when run as `python scripts/ask.py` from the repo root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import chromadb

from rag.generator import generate
from rag.ingest import COLLECTION_NAME, PERSIST_DIR, ingest
from rag.retriever import HybridRetriever


def index_exists() -> bool:
    """True if the Chroma collection exists and is non-empty."""
    try:
        client = chromadb.PersistentClient(path=PERSIST_DIR)
        return client.get_collection(COLLECTION_NAME).count() > 0
    except Exception:
        return False


def main() -> None:
    parser = argparse.ArgumentParser(description="Ask the vanilla RAG baseline a question.")
    parser.add_argument("query", help="The question to ask")
    parser.add_argument("--top-k", type=int, default=4, help="Chunks to retrieve (default 4)")
    parser.add_argument("--reingest", action="store_true", help="Rebuild the index first")
    args = parser.parse_args()

    if args.reingest or not index_exists():
        print("Building index from data/corpus/ ...")
        n = ingest()
        print(f"  ingested {n} chunks\n")

    retriever = HybridRetriever()
    chunks = retriever.retrieve(args.query, top_k=args.top_k)

    print("Retrieved context:")
    for i, c in enumerate(chunks):
        preview = c["text"][:100].replace("\n", " ")
        print(f"  [{i + 1}] ({c['source']}) {preview}...")

    print("\nGenerating answer (CPU — this can take a minute)...\n")
    answer = generate(args.query, chunks)
    print(f"Answer:\n{answer}")


if __name__ == "__main__":
    main()
