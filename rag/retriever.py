"""Hybrid retrieval: BM25 (lexical) + dense (bge-small via Chroma), fused
with reciprocal-rank fusion (RRF).

Why hybrid: dense retrieval catches paraphrases ("how hot do reefs get" ->
"thermal stress"), BM25 catches exact rare terms (names, numbers) that small
embedding models blur. RRF combines the two using only ranks, so we never
have to put cosine similarities and BM25 scores on a common scale.
"""

import re

import chromadb
from rank_bm25 import BM25Okapi

from rag.ingest import (
    BGE_QUERY_PREFIX,
    COLLECTION_NAME,
    PERSIST_DIR,
    get_embedder,
)


def _tokenize(text: str) -> list[str]:
    """Lowercase alphanumeric tokens — all BM25 needs at this scale."""
    return re.findall(r"[a-z0-9]+", text.lower())


def reciprocal_rank_fusion(rankings: list[list[str]], k: int = 60) -> list[str]:
    """Fuse ranked id lists: score(id) = sum over lists of 1 / (k + rank).

    k=60 is the standard constant from the RRF paper (Cormack et al. 2009);
    it damps the gap between rank 1 and rank 2 so one list can't dominate.
    """
    scores: dict[str, float] = {}
    for ranking in rankings:
        for rank, chunk_id in enumerate(ranking):
            scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (k + rank + 1)
    return sorted(scores, key=scores.get, reverse=True)


class HybridRetriever:
    """Loads the Chroma collection once, builds BM25 over the same chunks."""

    def __init__(self, persist_dir: str = PERSIST_DIR, collection_name: str = COLLECTION_NAME):
        client = chromadb.PersistentClient(path=persist_dir)
        self.collection = client.get_collection(collection_name)
        self.embedder = get_embedder()

        # Pull every chunk out of Chroma to build the BM25 index. One source
        # of truth: BM25 and dense search always see identical chunks.
        all_chunks = self.collection.get(include=["documents", "metadatas"])
        self.texts: dict[str, str] = dict(zip(all_chunks["ids"], all_chunks["documents"]))
        self.metas: dict[str, dict] = dict(zip(all_chunks["ids"], all_chunks["metadatas"]))

        # Derive the BM25 id<->document alignment from self.texts rather than
        # trusting that collection.get() returns ids and documents in the same
        # order. Chroma doesn't guarantee that ordering across versions; if it
        # ever drifted, BM25 would score one chunk's text but return another
        # chunk's id. Indexing texts[id] for each id makes the pairing explicit.
        self.ids: list[str] = list(self.texts.keys())
        self.bm25 = BM25Okapi([_tokenize(self.texts[cid]) for cid in self.ids])

    def _dense_search(self, query: str, k: int) -> list[str]:
        """Ranked chunk ids by cosine similarity. Note the bge query prefix."""
        emb = self.embedder.encode(BGE_QUERY_PREFIX + query, normalize_embeddings=True)
        res = self.collection.query(query_embeddings=[emb.tolist()], n_results=k)
        return res["ids"][0]

    def _bm25_search(self, query: str, k: int) -> list[str]:
        """Ranked chunk ids by BM25 score."""
        scores = self.bm25.get_scores(_tokenize(query))
        ranked = sorted(range(len(self.ids)), key=lambda i: scores[i], reverse=True)
        return [self.ids[i] for i in ranked[:k]]

    def retrieve(self, query: str, top_k: int = 4) -> list[dict]:
        """Top-k chunks after RRF fusion of dense and BM25 rankings.

        Each branch fetches 2*top_k candidates so fusion has real overlap
        to work with before we cut to top_k.
        """
        pool = min(2 * top_k, len(self.ids))
        fused = reciprocal_rank_fusion(
            [self._dense_search(query, pool), self._bm25_search(query, pool)]
        )
        return [
            {"id": cid, "text": self.texts[cid], "source": self.metas[cid]["source"]}
            for cid in fused[:top_k]
        ]
