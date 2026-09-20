"""End-to-end RAG pipeline: chunking, embedding, hybrid retrieval."""

from __future__ import annotations

import hashlib
import math
import re
from collections import Counter
from dataclasses import dataclass

from agentic_platform.observability.tracing import traced_span

_TOKEN_RE = re.compile(r"[a-z0-9]+")
_EMBEDDING_DIM = 64


def _tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


def _hash_embedding(tokens: list[str], dim: int = _EMBEDDING_DIM) -> list[float]:
    vector = [0.0] * dim
    for token in tokens:
        idx = int(hashlib.blake2b(token.encode(), digest_size=4).hexdigest(), 16) % dim
        vector[idx] += 1.0
    norm = math.sqrt(sum(v * v for v in vector)) or 1.0
    return [v / norm for v in vector]


def _cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b, strict=True))


@dataclass(slots=True, frozen=True)
class Chunk:
    doc_id: str
    chunk_id: str
    text: str
    source: str


@dataclass(slots=True)
class IndexedChunk:
    chunk: Chunk
    embedding: list[float]
    token_counts: Counter[str]


@dataclass(slots=True, frozen=True)
class RetrievalResult:
    chunk: Chunk
    score: float
    dense_score: float
    lexical_score: float


def chunk_document(
    doc_id: str, text: str, *, source: str, chunk_size: int = 200, overlap: int = 40
) -> list[Chunk]:
    if chunk_size <= overlap:
        raise ValueError("chunk_size must exceed overlap")
    words = text.split()
    if not words:
        return []
    chunks: list[Chunk] = []
    step = chunk_size - overlap
    start = 0
    i = 0
    while start < len(words):  # pragma: no branch - loop always exits via the break below
        window = words[start : start + chunk_size]
        chunks.append(
            Chunk(doc_id=doc_id, chunk_id=f"{doc_id}::{i}", text=" ".join(window), source=source)
        )
        if start + chunk_size >= len(words):
            break
        start += step
        i += 1
    return chunks


class HybridRetriever:
    def __init__(self, *, dense_weight: float = 0.6) -> None:
        if not 0.0 <= dense_weight <= 1.0:
            raise ValueError("dense_weight must be in [0, 1]")
        self._dense_weight = dense_weight
        self._index: list[IndexedChunk] = []

    def index(self, chunks: list[Chunk]) -> None:
        with traced_span("rag.index", chunk_count=len(chunks)):
            for chunk in chunks:
                tokens = _tokenize(chunk.text)
                self._index.append(
                    IndexedChunk(
                        chunk=chunk, embedding=_hash_embedding(tokens), token_counts=Counter(tokens)
                    )
                )

    @property
    def size(self) -> int:
        return len(self._index)

    def retrieve(self, query: str, *, top_k: int = 5) -> list[RetrievalResult]:
        if top_k <= 0:
            raise ValueError("top_k must be positive")
        query_tokens = _tokenize(query)
        query_embedding = _hash_embedding(query_tokens)
        query_terms = set(query_tokens)

        with traced_span("rag.retrieve", top_k=top_k, index_size=self.size) as span:
            results: list[RetrievalResult] = []
            for entry in self._index:
                dense = _cosine(query_embedding, entry.embedding)
                overlap = sum(entry.token_counts[t] for t in query_terms)
                lexical = overlap / (sum(entry.token_counts.values()) or 1)
                combined = self._dense_weight * dense + (1 - self._dense_weight) * lexical
                results.append(
                    RetrievalResult(
                        chunk=entry.chunk, score=combined, dense_score=dense, lexical_score=lexical
                    )
                )
            results.sort(key=lambda r: r.score, reverse=True)
            span.attributes["returned"] = min(top_k, len(results))
            return results[:top_k]
