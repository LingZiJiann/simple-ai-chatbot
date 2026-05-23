# Transcript: Vector Retrieval with Cosine Similarity Search

---

## 1. Requirements

**User:**
> Help me implement retrieval based on user query to get back the most relevant prompt, use cosine similarity as a starting point.
>
> Requirements:
> 1. Create a POST endpoint that accepts a search query
> 2. Embed the user query into a vector using the same embedding model as the chunks
> 3. Search for the most similar chunks using cosine similarity
> 4. Return top-K results ranked by relevance score
> 5. Return original chunk metadata (URL, title, price, text) along with similarity scores
> 6. Integrate with the existing Milvus vector store from the scraping pipeline

---

## 2. Design Decisions

### Embedding Model Consistency

> "Make sure the retrieval uses the same embedding model as the vector store"

**Decision:** Reuse `sentence-transformers.SentenceTransformer("paraphrase-MiniLM-L6-v2")` in both storage and retrieval paths. This ensures queries and chunks are comparable in the same semantic space.

### Similarity Metric Selection

> "Use cosine similarity as a starting point"

**Justification:** 
- Cosine similarity is scale-invariant — direction of vectors matters, not magnitude
- Produces normalized scores in range [0, 1] (interpretable as percentage match)
- Milvus native support via `metric_type="COSINE"` 
- Fast computation and semantically sound for embeddings

### Top-K Results Limiting

> "How many results should be returned by default?"

**Decision:** Default to `top_k=5` with allowed range `1 ≤ top_k ≤ 20` via Pydantic validation. Prevents excessive results while allowing flexibility.

### Result Ranking

> "Should results be ranked by score or in retrieval order?"

**Decision:** Always rank by cosine similarity score in descending order (highest score first). Users expect most relevant results first, regardless of how Milvus orders internal results.

### API Endpoint Design

> "What should the endpoint path be and what data should it return?"

**Decision:** 
- Endpoint: `POST /api/v1/retrieve`
- Input: `SearchRequest` with `query` and `top_k`
- Output: `SearchResponse` with original query and list of `SearchResult` objects
- Each result includes: chunk_id, source_url, chunk_index, text, char_count, page_title, price_gbp, score

This mirrors the scraper endpoint structure for consistency.

---

