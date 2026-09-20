import pytest

from agentic_platform.rag.pipeline import Chunk, HybridRetriever, chunk_document


def test_chunk_document_basic() -> None:
    text = " ".join(f"word{i}" for i in range(500))
    chunks = chunk_document("doc1", text, source="test", chunk_size=200, overlap=40)
    assert len(chunks) >= 2
    assert all(c.doc_id == "doc1" for c in chunks)


def test_chunk_document_empty_text_returns_empty() -> None:
    assert chunk_document("doc1", "", source="test") == []


def test_chunk_document_rejects_bad_overlap() -> None:
    with pytest.raises(ValueError, match="chunk_size must exceed overlap"):
        chunk_document("doc1", "a b c", source="test", chunk_size=10, overlap=10)


def test_hybrid_retriever_ranks_relevant_chunk_first() -> None:
    retriever = HybridRetriever()
    retriever.index(
        [
            Chunk("d1", "d1::0", "refunds are processed within five business days", "kb"),
            Chunk("d2", "d2::0", "unrelated content about weather patterns", "kb"),
        ]
    )
    results = retriever.retrieve("refund policy", top_k=1)
    assert results[0].chunk.doc_id == "d1"
    assert results[0].score > 0


def test_hybrid_retriever_rejects_bad_weight() -> None:
    with pytest.raises(ValueError, match="dense_weight"):
        HybridRetriever(dense_weight=2.0)


def test_hybrid_retriever_rejects_bad_top_k() -> None:
    retriever = HybridRetriever()
    with pytest.raises(ValueError, match="top_k must be positive"):
        retriever.retrieve("q", top_k=0)


def test_hybrid_retriever_empty_index_returns_empty() -> None:
    retriever = HybridRetriever()
    assert retriever.retrieve("anything") == []
    assert retriever.size == 0


def test_chunk_document_exact_boundary_avoids_empty_final_chunk() -> None:
    words = [f"w{i}" for i in range(160)]
    text = " ".join(words)
    chunks = chunk_document("doc1", text, source="test", chunk_size=200, overlap=40)
    assert len(chunks) == 1
    assert chunks[0].text == text
