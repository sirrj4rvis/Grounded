"""Ingest a corpus into a local ChromaDB collection.

Pipeline: load documents from the configured SOURCE -> chunk into overlapping
word windows -> embed with BAAI/bge-small-en-v1.5 (CPU, batched) -> store in a
persistent Chroma collection. Chroma is the single source of truth for chunks:
the retriever reads chunk texts back out of it to build the BM25 index, so we
never keep two copies of the corpus that can drift apart.

Corpus source is configurable (env GROUNDED_CORPUS):
  "wikipedia" (default) — a subset of a free HF Wikipedia dataset, so many
                          general-knowledge questions have grounding. Articles
                          beyond the subset correctly fall out of corpus -> the
                          pipeline abstains rather than guessing.
  "local"               — the small .txt/.md demo docs in data/corpus/.

Run:  python -m rag.ingest                      # uses GROUNDED_CORPUS (default wikipedia)
      GROUNDED_CORPUS=local python -m rag.ingest
"""

import os
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

# --- Defaults (kept here so retriever.py imports them and stays in sync) ---
CORPUS_DIR = Path("data/corpus")
PERSIST_DIR = "data/chroma"
COLLECTION_NAME = "grounded_corpus"
EMBED_MODEL = "BAAI/bge-small-en-v1.5"

# bge models are trained with this prefix on the QUERY side only. Passages are
# embedded without it; forgetting this asymmetry silently degrades retrieval.
BGE_QUERY_PREFIX = "Represent this sentence for searching relevant passages: "

# --- Corpus source config (all env-overridable so the corpus is swappable) ---
CORPUS_SOURCE = os.environ.get("GROUNDED_CORPUS", "wikipedia")  # "wikipedia" | "local"
WIKI_DATASET = os.environ.get("GROUNDED_WIKI_DATASET", "wikimedia/wikipedia")
WIKI_CONFIG = os.environ.get("GROUNDED_WIKI_CONFIG", "20231101.simple")  # Simple English
WIKI_LIMIT = int(os.environ.get("GROUNDED_WIKI_LIMIT", "4000"))  # articles to ingest
EMBED_BATCH = 256  # chunks per embed/add batch (caps memory, gives progress)


def get_embedder() -> SentenceTransformer:
    """Load the embedding model once (CPU). ~130 MB, a few seconds to load."""
    return SentenceTransformer(EMBED_MODEL, device="cpu")


def chunk_text(text: str, chunk_words: int = 180, overlap_words: int = 40) -> list[str]:
    """Split text into overlapping word windows.

    Simple and robust: never produces empty/huge chunks. The overlap keeps
    sentences that straddle a boundary retrievable from at least one chunk.
    """
    words = text.split()
    if len(words) <= chunk_words:
        return [" ".join(words)] if words else []
    chunks = []
    step = chunk_words - overlap_words
    for start in range(0, len(words), step):
        window = words[start : start + chunk_words]
        if len(window) < overlap_words and chunks:
            break  # tail already covered by the previous chunk's overlap
        chunks.append(" ".join(window))
    return chunks


def _iter_local(corpus_dir: Path):
    """Yield (doc_id, source_label, text) for each .txt/.md file."""
    found = False
    for path in sorted(corpus_dir.glob("*")):
        if path.suffix.lower() in {".txt", ".md"}:
            found = True
            yield path.name, path.name, path.read_text(encoding="utf-8")
    if not found:
        raise FileNotFoundError(f"No .txt/.md files in {corpus_dir.resolve()}")


def _iter_wikipedia(limit: int):
    """Stream `limit` articles from the HF Wikipedia subset (no full download)."""
    from datasets import load_dataset

    ds = load_dataset(WIKI_DATASET, WIKI_CONFIG, split="train", streaming=True)
    for i, art in enumerate(ds):
        if i >= limit:
            break
        title = art["title"].strip()
        yield f"wiki-{art['id']}", title, art["text"]


def iter_documents():
    """Dispatch to the configured corpus source -> (doc_id, source_label, text)."""
    if CORPUS_SOURCE == "local":
        yield from _iter_local(CORPUS_DIR)
    elif CORPUS_SOURCE == "wikipedia":
        yield from _iter_wikipedia(WIKI_LIMIT)
    else:
        raise ValueError(f"unknown GROUNDED_CORPUS={CORPUS_SOURCE!r} (use 'wikipedia' or 'local')")


def ingest(persist_dir: str = PERSIST_DIR, collection_name: str = COLLECTION_NAME) -> int:
    """(Re)build the Chroma collection from the configured corpus. Returns chunk count.

    We embed with sentence-transformers ourselves (not Chroma's built-in
    embedder) so the model is explicit and identical at index and query time.
    Embedding/adding is batched to cap memory and show progress on big corpora.
    """
    client = chromadb.PersistentClient(path=persist_dir)
    try:
        client.delete_collection(collection_name)  # full rebuild: no stale chunks
    except Exception:
        pass
    collection = client.create_collection(
        collection_name, metadata={"hnsw:space": "cosine"}  # bge compared by cosine
    )

    # Gather chunks first. Each stored chunk is prefixed with its source/title so
    # the chunk is self-describing for both retrieval and the generator's context.
    ids, texts, metas = [], [], []
    n_docs = 0
    for doc_id, source, body in iter_documents():
        n_docs += 1
        for i, chunk in enumerate(chunk_text(body)):
            ids.append(f"{doc_id}::c{i}")
            texts.append(f"{source}: {chunk}" if source else chunk)
            metas.append({"source": source, "chunk_index": i})
    total = len(ids)
    print(f"Loaded {n_docs} documents -> {total} chunks (source={CORPUS_SOURCE}). Embedding...", flush=True)

    embedder = get_embedder()
    for start in range(0, total, EMBED_BATCH):
        sl = slice(start, start + EMBED_BATCH)
        # No query prefix here — passages are embedded bare (see BGE_QUERY_PREFIX).
        emb = embedder.encode(texts[sl], normalize_embeddings=True, show_progress_bar=False)
        collection.add(ids=ids[sl], documents=texts[sl], embeddings=emb.tolist(), metadatas=metas[sl])
        done = min(start + EMBED_BATCH, total)
        if done % (EMBED_BATCH * 8) == 0 or done == total:
            print(f"  embedded {done}/{total}", flush=True)
    return total


if __name__ == "__main__":
    import time

    t0 = time.time()
    n = ingest()
    print(f"Ingested {n} chunks into '{COLLECTION_NAME}' at {PERSIST_DIR}/ in {time.time() - t0:.0f}s")
