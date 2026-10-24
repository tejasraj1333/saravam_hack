"""Local TF-IDF based retrieval — zero API cost.

Uses scikit-learn for TF-IDF vectorisation and cosine similarity.
Designed as a drop-in retrieval engine that can be swapped for
a proper vector DB in production.
"""

from __future__ import annotations

import logging
import re
from typing import Optional

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.models import DocumentChunk

logger = logging.getLogger(__name__)


class LocalVectorIndex:
    """In-memory TF-IDF index for document chunks."""

    def __init__(self) -> None:
        self._chunks: dict[str, DocumentChunk] = {}  # chunk_id → chunk
        self._doc_chunks: dict[str, list[str]] = {}   # doc_id → [chunk_ids]
        self._vectorizer: TfidfVectorizer | None = None
        self._matrix = None
        self._chunk_order: list[str] = []  # maintains order for matrix rows
        self._dirty = True

    def add_chunks(self, chunks: list[DocumentChunk]) -> None:
        """Add chunks and mark index for rebuild."""
        for chunk in chunks:
            self._chunks[chunk.chunk_id] = chunk
            self._doc_chunks.setdefault(chunk.document_id, []).append(chunk.chunk_id)
        self._dirty = True
        logger.info("Added %d chunks to index (total: %d)", len(chunks), len(self._chunks))

    def remove_document(self, document_id: str) -> int:
        """Remove all chunks for a document. Returns count removed."""
        chunk_ids = self._doc_chunks.pop(document_id, [])
        for cid in chunk_ids:
            self._chunks.pop(cid, None)
        if chunk_ids:
            self._dirty = True
        return len(chunk_ids)

    def _rebuild(self) -> None:
        """Rebuild TF-IDF matrix from all chunks."""
        if not self._chunks:
            self._vectorizer = None
            self._matrix = None
            self._chunk_order = []
            self._dirty = False
            return

        self._chunk_order = list(self._chunks.keys())
        texts = [self._chunks[cid].content for cid in self._chunk_order]

        self._vectorizer = TfidfVectorizer(
            max_features=10000,
            stop_words="english",
            ngram_range=(1, 2),
            sublinear_tf=True,
        )
        self._matrix = self._vectorizer.fit_transform(texts)
        self._dirty = False
        logger.info("Rebuilt TF-IDF index with %d chunks", len(self._chunk_order))

    def search(
        self,
        query: str,
        document_ids: list[str] | None = None,
        top_k: int = 5,
        min_score: float = 0.05,
    ) -> list[tuple[DocumentChunk, float]]:
        """Retrieve relevant chunks for a query.

        Args:
            query: The search query text.
            document_ids: Optional filter to specific documents.
            top_k: Maximum results to return.
            min_score: Minimum cosine similarity threshold.

        Returns:
            List of (chunk, score) tuples sorted by relevance.
        """
        if self._dirty:
            self._rebuild()

        if self._vectorizer is None or self._matrix is None:
            return []

        query_vec = self._vectorizer.transform([query])
        scores = cosine_similarity(query_vec, self._matrix).flatten()

        # Filter by document IDs if specified
        candidates = []
        for idx, score in enumerate(scores):
            if score < min_score:
                continue
            chunk_id = self._chunk_order[idx]
            chunk = self._chunks[chunk_id]
            if document_ids and chunk.document_id not in document_ids:
                continue
            candidates.append((chunk, float(score)))

        # Sort by score descending
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[:top_k]

    def get_chunk(self, chunk_id: str) -> DocumentChunk | None:
        return self._chunks.get(chunk_id)

    def get_document_chunks(self, document_id: str) -> list[DocumentChunk]:
        chunk_ids = self._doc_chunks.get(document_id, [])
        return [self._chunks[cid] for cid in chunk_ids if cid in self._chunks]

    @property
    def total_chunks(self) -> int:
        return len(self._chunks)


# Singleton
_index: LocalVectorIndex | None = None


def get_vector_index() -> LocalVectorIndex:
    global _index
    if _index is None:
        _index = LocalVectorIndex()
    return _index
