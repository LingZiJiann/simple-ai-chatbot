# Vector Retrieval & Semantic Search Documentation

## Overview

The retrieval module provides a FastAPI-based service for semantic similarity search over stored embeddings. It enables users to find relevant content based on meaning rather than keyword matching.

The complete retrieval pipeline includes:
1. **Query Embedding**: Converting user queries into dense vector embeddings
2. **Similarity Search**: Finding the most semantically similar chunks using cosine similarity
3. **Result Ranking**: Ranking results by relevance score
4. **Metadata Preservation**: Returning original chunk information (URL, title, price) with results

The system integrates with the web scraping pipeline—chunks extracted by the scraper are automatically embedded and stored in the vector database, making them immediately searchable through the retrieval API.

---

## Architecture

### Components

1. **VectorStore** (`vectorstore/store.py`) - Milvus integration and embedding management
2. **Router** (`retrieval/router.py`) - FastAPI endpoint definitions
3. **Schemas** (`retrieval/schemas.py`) - Pydantic data models for requests and responses

### Data Flow

```
User Query
    ↓
[POST /api/v1/retrieve]
    ↓
Query Embedding (SentenceTransformer)
    ↓
Vector Similarity Search (Milvus)
    ↓
Result Ranking (by cosine similarity score)
    ↓
[SearchResponse] with ranked chunks
```

---

## Core Concepts

### Embeddings

**What are embeddings?**
Embeddings are dense vectors that represent the semantic meaning of text. Each chunk is converted into a fixed-size vector that captures its conceptual meaning, allowing similar content to have similar vectors.

- **Embedding Model**: `paraphrase-MiniLM-L6-v2` (from Hugging Face)
- **Vector Dimension**: 384-dimensional vectors
- **Similarity Metric**: Cosine similarity (measures angle between vectors, 0 = orthogonal, 1 = identical)
- **Inference**: Non-linear, one-way transformation—queries and chunks encoded with the same model are directly comparable

### Vector Similarity Search

The retrieval engine uses **cosine similarity** to find the most relevant chunks:

1. Encode the user's query into a 384-dim vector
2. Search the Milvus vector database for the K nearest neighbors
3. Return results ranked by similarity score (higher = more similar)
4. Scores range from 0 to 1, where 1.0 is a perfect match

### Milvus Vector Database

**Milvus** is an open-source vector database optimized for:
- High-dimensional vector similarity search
- Low-latency queries across millions of vectors
- Horizontal scalability and high throughput

**Collection Schema**:
- `chunk_id` (VARCHAR, primary key): Unique identifier for the chunk
- `source_url` (VARCHAR): URL of the page the chunk came from
- `chunk_index` (INT64): Sequential chunk number within the page
- `text` (VARCHAR): Chunk text content (capped at 1024 chars)
- `char_count` (INT64): Original character count of the chunk
- `page_title` (VARCHAR): Title of the source page
- `price_gbp` (FLOAT): Product price in GBP (stored as `-1.0` if null)
- `vector` (FLOAT_VECTOR, dim=384): The embedding vector

**Indexing Strategy**:
- Index Type: FLAT (exhaustive search)
- Metric: COSINE
- Suitable for: Exact similarity search (exact results, not approximate)

### Metadata Attachment

All metadata from the original chunks (URL, title, price, etc.) is preserved and returned with search results, enabling:
- **Attribution**: Users can click back to the source
- **Filtering**: Post-search filtering by price, domain, etc.
- **Context**: Rich information about each result

---

## API Endpoints

### `POST /api/v1/retrieve`

Search for chunks semantically similar to a query.

#### Request Schema

```json
{
  "query": "affordable travel guides",
  "top_k": 5
}
```

| Field | Type | Default | Constraints | Description |
|-------|------|---------|-------------|-------------|
| `query` | `str` | Required | - | Natural language query text to search for |
| `top_k` | `int` | `5` | `1 ≤ top_k ≤ 20` | Number of top results to return |

#### Response Schema

```json
{
  "query": "affordable travel guides",
  "results": [
    {
      "chunk_id": "a1b2c3d4e5f6g7h8",
      "source_url": "https://books.toscrape.com/catalogue/travel_book_1/index.html",
      "chunk_index": 0,
      "text": "Budget Travel Guide to Europe: This comprehensive guide covers...",
      "char_count": 245,
      "page_title": "Budget Travel Guide to Europe",
      "price_gbp": 12.99,
      "score": 0.87
    },
    {
      "chunk_id": "b2c3d4e5f6g7h8i9",
      "source_url": "https://books.toscrape.com/catalogue/travel_book_2/index.html",
      "chunk_index": 1,
      "text": "Backpacking Through Asia: A budget traveler's handbook...",
      "char_count": 312,
      "page_title": "Backpacking Through Asia",
      "price_gbp": 9.99,
      "score": 0.82
    }
  ]
}
```

| Field | Type | Description |
|-------|------|-------------|
| `query` | `str` | The query text that was searched |
| `results` | `SearchResult[]` | List of similar chunks, ranked by relevance |

#### SearchResult Schema Details

| Field | Type | Description |
|-------|------|-------------|
| `chunk_id` | `str` | Unique identifier for the chunk |
| `source_url` | `str` | Full URL of the page this chunk came from |
| `chunk_index` | `int` | Sequential index of this chunk within its page |
| `text` | `str` | Content of the chunk (truncated at 1024 chars) |
| `char_count` | `int` | Original character count before truncation |
| `page_title` | `str` | Title of the source page |
| `price_gbp` | `float \| null` | Product price in GBP, if present; null if not found |
| `score` | `float` | Cosine similarity score (0-1, higher = more similar) |

#### Example Usage

```bash
curl -X POST http://localhost:8000/api/v1/retrieve \
  -H "Content-Type: application/json" \
  -d '{
    "query": "travel guides under 15 pounds",
    "top_k": 10
  }'
```

#### HTTP Status Codes

- **200 OK**: Search completed successfully
- **400 Bad Request**: Invalid request (e.g., `top_k` out of range)
- **500 Internal Server Error**: Database or embedding model error

---

## VectorStore Details

### Initialization

The VectorStore is initialized once at application startup via the FastAPI lifespan context:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    Path(settings.milvus_db_path).parent.mkdir(parents=True, exist_ok=True)
    store = VectorStore(settings.milvus_db_path)
    app.state.vector_store = store
    yield
    store.close()
```

This ensures:
- The Milvus database directory exists
- A single VectorStore instance serves all requests
- The database is properly closed on shutdown

### Embedding Process

When chunks are uperted into the vector store:

1. **Extract Texts**: Get the text content from each chunk
2. **Encode**: Convert texts to embeddings using `SentenceTransformer("paraphrase-MiniLM-L6-v2")`
3. **Normalize**: Convert tensor embeddings to Python lists for Milvus
4. **Truncate**: Cap text at 1024 chars and page_title at 512 chars
5. **Handle Nulls**: Convert null prices to `-1.0` sentinel value
6. **Upsert**: Insert or update rows in Milvus collection

Example:
```python
store.upsert_chunks(chunks)  # Returns count of rows written
```

### Search Process

When a query is submitted:

1. **Encode Query**: Convert query text to 384-dim vector using the same SentenceTransformer model
2. **Vector Search**: Query Milvus with the embedding vector, requesting top K results
3. **Retrieve Fields**: Get chunk metadata alongside the distance score
4. **Normalize Results**: Convert Milvus distance to readable format, restore null prices
5. **Sort Results**: Order by similarity score (descending)

```python
results = store.search(query="travel guides", top_k=5)
# Returns: [{"chunk_id": "...", "score": 0.87, ...}, ...]
```

### Thread Safety

The VectorStore uses Milvus client connections which are not async-safe. The router handles this via `asyncio.to_thread`:

```python
raw = await asyncio.to_thread(store.search, query, top_k)
```

This offloads the blocking I/O to a thread pool, keeping the event loop responsive.

---

## Integration with Web Scraping

The retrieval system is tightly integrated with the web scraping pipeline:

1. **Scraper** extracts chunks from web pages
2. **Router** (`/scrape` endpoint) returns chunks and stores them in the database
3. **VectorStore** automatically embeds and indexes chunks via `upsert_chunks()`
4. **Retriever** (`/retrieve` endpoint) searches the indexed chunks

Example flow:
```
POST /api/v1/scrape → [pages crawled, chunks created]
    ↓ (inside router)
vectorstore.upsert_chunks(chunks) → [embeddings created, Milvus indexed]
    ↓
POST /api/v1/retrieve → [semantic search over indexed chunks]
```

---

## Error Handling

### Query Validation

The `SearchRequest` model validates input:
- `top_k` must be between 1 and 20 (prevents excessive results or invalid queries)
- `query` must be non-empty string

Validation errors return **400 Bad Request**:
```json
{
  "detail": [
    {
      "type": "value_error",
      "loc": ["body", "top_k"],
      "msg": "ensure this value is less than or equal to 20"
    }
  ]
}
```

### Database Errors

If the vector store is unavailable or embedding fails:
- Connection errors to Milvus return **500 Internal Server Error**
- Model loading failures prevent app startup (caught during `lifespan`)

Errors are logged with full context:
```
ERROR retrieval.router: Exception during retrieve: [error details]
```

### Empty Results

A valid search with no matches returns:
```json
{
  "query": "obscure niche topic",
  "results": []
}
```

This is **not** an error—it indicates the query had no similar chunks.

---

## Configuration

Configuration is loaded from `config/config.py` and can be overridden via environment variables:

| Setting | Type | Default | Purpose |
|---------|------|---------|---------|
| `milvus_db_path` | `str` | (from config) | File path to Milvus database directory |

### Environment Variables

```bash
# Override Milvus database location
export MILVUS_DB_PATH="/custom/path/milvus.db"
```

---

## Usage Examples

### Basic Search

Search for 5 most relevant chunks:

```python
import httpx

async with httpx.AsyncClient() as client:
    response = await client.post(
        "http://localhost:8000/api/v1/retrieve",
        json={
            "query": "affordable travel guides",
            "top_k": 5
        }
    )
    result = response.json()
    for r in result['results']:
        print(f"[{r['score']:.2f}] {r['page_title']} - {r['source_url']}")
```

### High-Quality Results Only

Search for high-confidence matches (score ≥ 0.8):

```python
response = await client.post(
    "http://localhost:8000/api/v1/retrieve",
    json={"query": "specific product name", "top_k": 10}
)
results = response.json()['results']
high_confidence = [r for r in results if r['score'] >= 0.8]
```

### Price-Aware Search

Find cheap travel guides:

```python
response = await client.post(
    "http://localhost:8000/api/v1/retrieve",
    json={"query": "travel guide", "top_k": 20}
)
results = response.json()['results']
affordable = [
    r for r in results 
    if r['price_gbp'] and r['price_gbp'] < 15
][:5]
```

### Direct VectorStore Usage

Use the store directly in Python:

```python
from src.vectorstore.store import VectorStore

store = VectorStore("/path/to/milvus.db")

# Embed and store chunks
chunks = [...]  # from scraper
store.upsert_chunks(chunks)

# Search for similar content
results = store.search("travel guides", top_k=5)

# Clean up
store.close()
```

---

## Implementation Details

### Embedding Model Selection

**paraphrase-MiniLM-L6-v2** was chosen for:
- **Speed**: Fast inference on CPU (< 100ms for typical queries)
- **Multilingual**: Supports 50+ languages
- **Compact**: 384-dim vectors (vs. 768+ for larger models)
- **Quality**: MTEB benchmark score of 58.89 (good balance of speed vs. accuracy)
- **Memory**: Low resource overhead (ideal for edge deployment)

### Dimension Trade-offs

384-dimensional vectors provide:
- **Semantic Richness**: Sufficient dimensionality to capture meaning nuances
- **Memory Efficiency**: Smaller than 768-dim or 1024-dim alternatives
- **Search Speed**: Faster similarity computation (cosine distance is O(d))
- **Database Size**: Smaller Milvus index footprint

### Cosine Similarity

Cosine similarity was chosen because:
- **Scale Invariant**: Magnitude of vectors doesn't matter, only direction
- **Normalized**: Always outputs value in range [0, 1] (interpretable as percentage match)
- **Fast Computation**: Efficient in vector databases
- **Semantic Soundness**: Aligns with how embeddings are trained

Formula:
```
similarity = dot(A, B) / (norm(A) * norm(B))
```

### Null Price Handling

Prices are stored using a sentinel value (`-1.0`) because:
- Milvus FLOAT field cannot represent SQL-like NULL
- Sentinel is outside realistic price range (prices ≥ 0)
- On retrieval, sentinels are converted back to Python `None`

---

## Performance Considerations

### Query Latency

For a typical query with 384-dim vectors and FLAT index:
- **Embedding**: ~50-100ms (transformer inference)
- **Search**: ~10-50ms (depends on collection size)
- **Total**: ~100-150ms for typical workloads

Scaling characteristics:
- FLAT index: O(n) scan (linear with collection size)
- To optimize for >1M vectors: consider IVF or HNSW index

### Memory Usage

- **Embedding Model**: ~80-100 MB in RAM (loaded once at startup)
- **Milvus Index**: ~1-2 MB per 1000 vectors (384-dim + metadata)
- **Connection Pool**: Milvus client uses single connection per process

Example memory for 100K chunks:
- Embeddings alone: ~150-200 MB
- With metadata: ~200-300 MB

### Database Size

Milvus stores vectors and metadata in a SQLite backend:
- Raw vector data: 384 floats × 4 bytes = 1536 bytes per vector
- Metadata overhead: ~500-1000 bytes per record
- Total: ~2-2.5 KB per chunk

100K chunks ≈ 200-250 MB on disk

### Search Optimization

To improve search performance:
1. **Increase `top_k`**: Marginally faster (same scan, early stopping)
2. **Filter by metadata**: Not natively supported in Milvus Lite—post-filter results
3. **Batch queries**: Multiple sequential queries are faster than single queries
4. **Index tuning**: Switch to IVF or HNSW for faster approximate search (accuracy trade-off)

---

## Troubleshooting

### No Results Returned

**Symptom**: Valid query returns empty `results` list

**Causes**:
- Vector store is empty (no chunks uperted yet)
- Query is too different from stored content
- Embedding model failed silently

**Solution**:
1. Verify chunks exist: Check Milvus collection via `store._client.num_entities(COLLECTION_NAME)`
2. Try broader query: Use simple, common terms first
3. Check logs: Look for embedding errors

### Very Low Similarity Scores

**Symptom**: All results have score < 0.5

**Causes**:
- Query is semantically far from content
- Content domain mismatch (e.g., searching for technical terms in travel docs)
- Embedding model limitations

**Solution**:
- Reformulate query in simpler terms
- Use more content from the target domain
- Consider fine-tuning the embedding model for your domain

### Slow Queries

**Symptom**: Search endpoint takes > 500ms

**Causes**:
- Large collection size (FLAT index has O(n) complexity)
- Slow embedding inference
- System resource contention

**Solution**:
1. Profile with logs: Check `retrieval.router` logs for timing
2. Upgrade model: Consider faster inference optimizations
3. Re-index: Switch to IVF index (`index_type="IVF_FLAT"`) for approximate search
4. Scale: Deploy Milvus on dedicated hardware

### Database Corruption

**Symptom**: Milvus client connection fails or raises errors

**Causes**:
- Unclean shutdown (previous instance still running)
- File system issues
- Corrupted database file

**Solution**:
1. Stop the application
2. Delete the Milvus database directory (`rm -rf $MILVUS_DB_PATH`)
3. Re-initialize by starting the app (empty collection will be created)
4. Re-upload chunks via `/scrape` endpoint

---

## Future Enhancements

- **Approximate Nearest Neighbor (ANN) Indexing**: Use IVF-FLAT or HNSW for >1M vector scale
- **Query Expansion**: Automatically generate related queries to improve coverage
- **Result Reranking**: Use a cross-encoder model to re-rank results for higher accuracy
- **Filters and Metadata Search**: Native metadata filtering in Milvus (SELECT with WHERE clause)
- **Hybrid Search**: Combine keyword search (BM25) with semantic search
- **Fine-tuning**: Fine-tune embedding model on domain-specific data
- **Multi-Vector Search**: Store multiple embeddings per chunk (title, body, metadata)
- **Caching**: LRU cache for frequent queries
- **Analytics**: Track search patterns, popular queries, null results
- **User Feedback Loop**: Learn from relevance feedback to improve rankings
