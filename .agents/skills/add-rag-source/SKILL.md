---
name: add-rag-source
description: Add a new document source into the HybridRetriever knowledge base in agentic-platform.
---

# Add a new RAG data source

Use this when asked to ingest a new document/knowledge source into the
retrieval pipeline.

## Steps

1. **Chunk the source** with `chunk_document(doc_id, text, source=..., chunk_size=200, overlap=40)`
   from `src/agentic_platform/rag/pipeline.py`. Keep `chunk_size > overlap`
   (enforced by a `ValueError` otherwise). Choose a stable, human-readable
   `doc_id` — it's used as a provenance key.

2. **Index it** via `HybridRetriever.index(chunks)`. If you're wiring a new
   ingestion path (e.g. reading from a directory, a database, or an API),
   add it as a method on a small ingestion helper — don't inline file/DB
   reads inside `AgenticPipeline`. Keep `HybridRetriever` free of any
   knowledge of *where* text came from; it only knows about `Chunk` objects.

3. **If replacing the embedding backend**: the current `_hash_embedding` in
   `rag/pipeline.py` is a deterministic, dependency-free stand-in for a real
   embedding model. To swap in a real model (OpenAI/Voyage/Cohere
   embeddings), replace `_hash_embedding` and `_tokenize`'s role, but keep
   the `HybridRetriever` public interface (`index`, `retrieve`, `size`)
   unchanged so the rest of the codebase (agents, tests) doesn't need to
   change.

4. **Write tests**:
   - Unit test that chunking produces the expected chunk count/boundaries
     for your new source's typical document length.
   - Unit or integration test that a representative query against the new
     source ranks the relevant chunk in the top-k.

5. **Consider retrieval quality**, not just plumbing: if your source has
   exact-match identifiers (SKUs, ticket IDs, error codes), verify the
   lexical scoring component (not just dense/embedding scoring) surfaces
   them — this is exactly what hybrid retrieval is for.

6. Run `make ci` before considering the task done.
