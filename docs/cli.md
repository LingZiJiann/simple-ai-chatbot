# RAG Chatbot CLI Documentation

## Overview

The CLI provides an interactive command-line interface for querying and inspecting retrieved chunks from the vector database. It enables developers to explore relevant search results without using Swagger UI, making it ideal for debugging, testing, and understanding the retrieval system's behavior.

The CLI is the first phase of a RAG (Retrieval-Augmented Generation) chatbot. It currently displays retrieved chunks with relevance scores and metadata. The architecture is designed to easily extend it with an LLM response generation step in the future.

---

## Architecture

### Components

1. **CLI Script** (`cli.py`) - Interactive REPL interface
2. **HTTP Client** - Calls the FastAPI retrieval endpoint
3. **Retrieval API** (`/api/v1/retrieve`) - Backend search endpoint (see [retrieval.md](retrieval.md))

### Data Flow

```
User Input (Terminal)
    ↓
[CLI → HTTP POST /api/v1/retrieve]
    ↓
Query Embedding & Vector Search (API)
    ↓
Ranked Chunks (JSON)
    ↓
Display in Terminal
```

The CLI is a lightweight HTTP client that communicates with the running FastAPI server. This approach:
- Avoids Milvus connection locks (server holds the connection)
- Keeps the CLI stateless and simple
- Allows reuse of the existing retrieval API
- Makes it easy to extend with LLM integration later

---

## Getting Started

### Prerequisites

- FastAPI server running on `http://localhost:8000`
- Chunks previously scraped and indexed (via `/api/v1/scrape` endpoint)

### Running the CLI

```bash
# Activate virtual environment (if using venv)
source .venv/bin/activate

# Run the CLI using uv
uv run cli.py

# Or run directly with Python
python cli.py
```

### Example Session

```
RAG Chatbot (chunk viewer mode)
Connected to http://localhost:8000
Type your query and press Enter. Type 'exit' or Ctrl+C to quit.
────────────────────────────────────────────────────────────

Query> travel guides

  #1  [score: 0.87]  Budget Travel Guide to Europe
      £12.99  |  https://books.toscrape.com/catalogue/travel_book_1/...
      "Budget Travel Guide to Europe: This comprehensive guide covers..."

  #2  [score: 0.82]  Backpacking Through Asia
      £9.99  |  https://books.toscrape.com/catalogue/travel_book_2/...
      "Backpacking Through Asia: A budget traveler's handbook..."

  2 chunks retrieved.

Query> python programming

  #1  [score: 0.95]  Learning Python
      £25.50  |  https://books.toscrape.com/catalogue/learning_python/...
      "Learning Python: Comprehensive guide for beginners and experts..."

  1 chunk retrieved.

Query> exit
```

---

## Usage

### Interactive Loop

The CLI operates as an interactive REPL:

1. **Startup**: Displays the welcome message and connects to the API
2. **Query Prompt**: `Query>` prompt appears, waiting for user input
3. **Input**: Type a natural language query (e.g., "travel guides", "python books")
4. **Results**: Top 5 chunks are displayed with scores and metadata
5. **Loop**: Prompt appears again for the next query
6. **Exit**: Type `exit`, `quit`, or press `Ctrl+C` to quit gracefully

### Output Format

Each result is displayed with:

```
  #N  [score: X.XX]  <Page Title>
      <Price>  |  <Source URL (truncated)>
      "<Text excerpt (truncated to 80 chars)>"
```

**Fields**:
- **#N**: Result rank (1 = most relevant)
- **score**: Cosine similarity score (0.0–1.0, higher = more relevant)
- **Page Title**: Title of the source page
- **Price**: Product price in GBP, or "(no price)" if not available
- **Source URL**: Full URL of the source, truncated for display
- **Text excerpt**: First ~80 characters of the chunk, truncated with `...`

### Entering Queries

```bash
Query> affordable travel guides
Query> python programming beginner
Query> machine learning tutorials
Query> [empty line] → ignored, re-prompts
Query> exit → gracefully exits
Query> quit → gracefully exits
Query> [Ctrl+C] → gracefully exits
```

**Query Tips**:
- Use natural language (the embedding model understands semantics)
- Longer, more specific queries yield more relevant results
- Empty input is ignored (no error, just re-prompts)
- Queries are case-insensitive

---

## Configuration

### API Endpoint

The CLI connects to `http://localhost:8000` by default. To use a different endpoint, edit `cli.py`:

```python
BASE_URL = "http://localhost:8000"  # Change this to your API URL
```

### Default Parameters

The CLI uses these fixed defaults:

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `top_k` | `5` | Number of chunks to retrieve |
| `timeout` | `10.0s` | HTTP request timeout |

To modify these, edit the `retrieve()` function in `cli.py`.

---

## Implementation Details

### Direct API Integration

The CLI calls the existing `/api/v1/retrieve` endpoint, which handles:
- Query validation (non-empty string)
- Embedding generation (SentenceTransformer)
- Vector similarity search (Milvus)
- Result ranking (by cosine similarity)

See [retrieval.md](retrieval.md) for endpoint details.

### Error Handling

The CLI gracefully handles common errors:

| Error | Behavior |
|-------|----------|
| **API unreachable** | Displays error message, re-prompts for next query |
| **Invalid query** | API returns 400, error shown, re-prompts |
| **No results** | Displays "No chunks found.", re-prompts |
| **Keyboard interrupt (Ctrl+C)** | Exits cleanly with newline |
| **EOF (e.g., piped input)** | Exits cleanly |

### HTTP Timeout

The CLI has a 10-second timeout per request. If the API takes longer:
```
Error: operation timed out after 10.0 seconds
```

For slow networks or large collections, increase the timeout in the `retrieve()` function.

---

## Future Enhancements

### Phase 2: LLM Response Generation

The CLI is designed to easily extend with an LLM that generates answers based on retrieved chunks:

```python
def display_chunks(chunks: list[dict]) -> None:
    # ... display chunks ...
    
    # Future: add LLM response
    answer = generate_answer(query, chunks)  # Call LLM with query + chunks
    print(f"Answer: {answer}")
```

The `retrieve()` function returns plain dictionaries containing:
- `text` - chunk content
- `source_url` - attribution link
- `page_title` - source title
- `score` - relevance score

These are ideal inputs for an LLM context window.

### Other Possible Extensions

- **Filtering**: Add `--price-max`, `--source-domain` flags to filter results
- **Output formats**: JSON, CSV, HTML output options
- **Caching**: Cache frequent queries to speed up responses
- **Multi-turn context**: Maintain conversation history for follow-up questions
- **Re-ranking**: Post-process results with a cross-encoder for higher accuracy

---

## Troubleshooting

### "Connected to http://localhost:8000" but no results

**Causes**:
- API is running but has no chunks indexed yet
- Query is semantically far from stored content
- Vector database is empty

**Solution**:
1. Verify chunks exist by calling `/api/v1/scrape` first to populate the database
2. Try simpler, more common queries
3. Check API logs for errors

### API Connection Refused

**Error**: `Connection refused` or `Temporary failure in name resolution`

**Causes**:
- FastAPI server is not running
- Server is on a different port
- Firewall is blocking localhost connections

**Solution**:
1. Start the API: `uvicorn main:app --reload`
2. Verify it's running: `curl http://localhost:8000/health`
3. Check the `BASE_URL` in `cli.py` matches your server

### Very Low Similarity Scores (< 0.5)

**Causes**:
- Query is semantically far from stored content
- Limited or mismatched domain (e.g., searching for technical terms in travel docs)
- Content diversity issues

**Solution**:
- Reformulate with simpler, more common terms
- Index more relevant content via the scraper
- Consider fine-tuning the embedding model for your domain

### Slow Queries (> 5 seconds)

**Causes**:
- Large vector collection (FLAT index is O(n))
- Slow network or API server
- Embedding inference overhead

**Solution**:
1. Check API logs to see where time is spent
2. Scale the API to faster hardware
3. For very large collections, consider switching to an approximate nearest neighbor (ANN) index (e.g., IVF-FLAT, HNSW)

### "No module named httpx"

The CLI requires `httpx`, which should be installed via `pyproject.toml`. Ensure your virtual environment is activated:

```bash
source .venv/bin/activate
# Or with uv:
uv run cli.py
```

---

## Code Reference

### Entry Point

**File**: `cli.py` at project root

**Key Functions**:

```python
def retrieve(query: str, top_k: int = 5) -> list[dict]:
    """Calls /api/v1/retrieve and returns chunks."""

def display_chunks(chunks: list[dict]) -> None:
    """Formats and prints chunks to terminal."""

def main() -> None:
    """Runs the interactive REPL loop."""
```

### Dependencies

- `httpx` - HTTP client for API calls (already in `pyproject.toml`)
- `sys` - Standard library for I/O

---

## Integration with Retrieval API

The CLI calls the same endpoint as Swagger UI. For detailed request/response schemas, see [retrieval.md#api-endpoints](retrieval.md#api-endpoints).

**Endpoint**: `POST /api/v1/retrieve`

**Request**:
```json
{
  "query": "travel guides",
  "top_k": 5
}
```

**Response**:
```json
{
  "query": "travel guides",
  "results": [
    {
      "chunk_id": "...",
      "source_url": "...",
      "chunk_index": 0,
      "text": "...",
      "char_count": 245,
      "page_title": "...",
      "price_gbp": 12.99,
      "score": 0.87
    }
  ]
}
```

---

## Examples

### Search for Book Recommendations

```bash
Query> fantasy novels under 20 pounds

  #1  [score: 0.89]  The Hobbit
      £15.99  |  https://books.toscrape.com/catalogue/the-hobbit/...
      "The Hobbit is a fantasy novel and children's book by J. R. R. Tolkien..."

  #2  [score: 0.87]  Percy Jackson and the Olympians
      £12.50  |  https://books.toscrape.com/catalogue/percy-jackson/...
      "An exciting fantasy adventure series for young readers..."

  2 chunks retrieved.
```

### Search for Educational Content

```bash
Query> python programming tutorial

  #1  [score: 0.93]  Python Crash Course
      £28.99  |  https://books.toscrape.com/catalogue/python-crash-course/...
      "Learn Python programming from scratch with hands-on projects and..."

  #2  [score: 0.89]  Automate the Boring Stuff
      £24.95  |  https://books.toscrape.com/catalogue/automate-boring/...
      "A practical guide to automating everyday tasks with Python..."

  2 chunks retrieved.
```

### Empty Results

```bash
Query> quantum teleportation physics

  No chunks found.
```

---

## Comparison with Swagger UI

| Feature | Swagger UI | CLI |
|---------|-----------|-----|
| **Access** | Browser-based | Terminal-based |
| **Query Speed** | Slower (UI overhead) | Faster (direct HTTP) |
| **Batch Queries** | One at a time | Multiple (REPL loop) |
| **Ease of Use** | Visual forms | Type directly |
| **Integration** | Manual | Scriptable (via stdin) |
| **Ideal For** | Exploration | Development/testing |

---

## Contributing

To extend the CLI:
1. Edit `cli.py` at the project root
2. Keep HTTP calls isolated in the `retrieve()` function
3. Keep display logic isolated in `display_chunks()`
4. Test with `uv run cli.py` or `python cli.py`

For bug reports or feature requests, see the project's contribution guidelines.
