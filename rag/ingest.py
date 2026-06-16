"""Ingest .txt/.md documents into a local ChromaDB collection.

Pipeline: read docs from data/corpus/ -> chunk into overlapping word windows
-> embed with BAAI/bge-small-en-v1.5 (CPU) -> store in a persistent Chroma
collection. Chroma is the single source of truth for chunks: the retriever
reads chunk texts back out of it to build the BM25 index, so we never have
two copies of the corpus that can drift apart.

Run directly to (re)build the index:  python -m rag.ingest
"""

from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

# --- Defaults (kept here so retriever.py imports them and stays in sync) ---
CORPUS_DIR = Path("data/corpus")
PERSIST_DIR = "data/chroma"
COLLECTION_NAME = "grounded_corpus"
EMBED_MODEL = "BAAI/bge-small-en-v1.5"

# bge models are trained with this prefix on the QUERY side only.
# Passages are embedded without it. Forgetting this asymmetry silently
# degrades retrieval quality, so it lives here next to the model name.
BGE_QUERY_PREFIX = "Represent this sentence for searching relevant passages: "


def get_embedder() -> SentenceTransformer:
    """Load the embedding model once (CPU). ~130 MB, a few seconds to load."""
    return SentenceTransformer(EMBED_MODEL, device="cpu")


def load_documents(corpus_dir: Path = CORPUS_DIR) -> list[tuple[str, str]]:
    """Return (doc_id, text) for every .txt/.md file in the corpus dir."""
    docs = []
    for path in sorted(corpus_dir.glob("*")):
        if path.suffix.lower() in {".txt", ".md"}:
            docs.append((path.name, path.read_text(encoding="utf-8")))
    if not docs:
        raise FileNotFoundError(f"No .txt/.md files found in {corpus_dir.resolve()}")
    return docs


def chunk_text(text: str, chunk_words: int = 180, overlap_words: int = 40) -> list[str]:
    """Split text into overlapping word windows.

    Word-window chunking is deliberately simple for the baseline: it never
    produces empty/huge chunks and is easy to reason about in the eval.
    The overlap keeps sentences that straddle a boundary retrievable from
    at least one chunk.
    """
    words = text.split()
    if len(words) <= chunk_words:
        return [" ".join(words)]
    chunks = []
    step = chunk_words - overlap_words
    for start in range(0, len(words), step):
        window = words[start : start + chunk_words]
        if len(window) < overlap_words and chunks:
            break  # tail already covered by the previous chunk's overlap
        chunks.append(" ".join(window))
    return chunks


def ingest(
    corpus_dir: Path = CORPUS_DIR,
    persist_dir: str = PERSIST_DIR,
    collection_name: str = COLLECTION_NAME,
) -> int:
    """(Re)build the Chroma collection from the corpus. Returns chunk count.

    We embed with sentence-transformers ourselves and hand Chroma raw vectors,
    rather than using Chroma's built-in embedder — so the model choice is
    explicit and identical at index time and query time.
    """
    client = chromadb.PersistentClient(path=persist_dir)

    # Drop and recreate: ingestion is cheap at this corpus size, and a full
    # rebuild avoids stale chunks when a source document changes.
    try:
        client.delete_collection(collection_name)
    except Exception:
        pass  # collection didn't exist yet
    collection = client.create_collection(
        collection_name,
        metadata={"hnsw:space": "cosine"},  # bge embeddings are compared by cosine
    )

    embedder = get_embedder()

    ids, texts, metadatas = [], [], []
    for doc_id, text in load_documents(corpus_dir):
        for i, chunk in enumerate(chunk_text(text)):
            ids.append(f"{doc_id}::chunk{i}")
            texts.append(chunk)
            metadatas.append({"source": doc_id, "chunk_index": i})

    # No query prefix here — passages are embedded bare (see BGE_QUERY_PREFIX).
    embeddings = embedder.encode(texts, normalize_embeddings=True, show_progress_bar=False)
    collection.add(ids=ids, documents=texts, embeddings=embeddings.tolist(), metadatas=metadatas)
    return len(ids)


if __name__ == "__main__":
    n = ingest()
    print(f"Ingested {n} chunks into '{COLLECTION_NAME}' at {PERSIST_DIR}/")
