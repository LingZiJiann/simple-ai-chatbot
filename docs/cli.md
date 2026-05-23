# RAG Chatbot CLI Documentation

## Overview

The CLI provides an interactive command-line interface for a complete RAG (Retrieval-Augmented Generation) chatbot with **multi-turn conversation support**. Users enter natural language queries, the system retrieves relevant chunks from the vector database, and Claude Haiku generates a grounded answer based on those chunks. The chatbot maintains conversation history and intelligently rewrites follow-up questions to improve retrieval accuracy.

Key features:
- **Semantic Search**: Retrieves the top 5 most relevant chunks using cosine similarity
- **LLM-Powered Answers**: Claude Haiku generates contextual answers based on retrieved chunks
- **Multi-Turn Conversation**: Maintains conversation history across turns; Claude references prior answers
- **Query Rewriting**: Rewrites vague follow-up questions (e.g., "tell me more about that") into standalone queries for better retrieval
- **Streamed Responses**: Answers stream word-by-word for a natural chatbot feel
- **Interactive Loop**: Run multiple queries in one session without restarting
- **No Server Required**: Works with a running FastAPI server; server holds Milvus connection

---

## Architecture

### Components

1. **CLI Script** (`cli.py`) - Interactive REPL interface at project root
2. **Retrieval Module** - HTTP client that calls the FastAPI `/api/v1/retrieve` endpoint
3. **LLM Generator** (`src/llm/generator.py`) - `AnswerGenerator` class that calls Claude Haiku
4. **Retrieval API** (`/api/v1/retrieve`) - Backend search endpoint (see [retrieval.md](retrieval.md))

### Data Flow

```
User Input (Terminal)
    ↓
[If history exists: Rewrite query via Claude Haiku (cheap LLM call)]
    ↓
[CLI → HTTP POST /api/v1/retrieve with (original or rewritten) query]
    ↓
Query Embedding & Vector Search (Milvus via API)
    ↓
Ranked Chunks (JSON response)
    ↓
[Display Chunks]
    ↓
[AnswerGenerator → Claude Haiku API with history + chunks]
    ↓
LLM generates answer using conversation history + chunks as context
    ↓
Stream answer to Terminal (word-by-word)
    ↓
Store original query and answer in conversation history (in-memory)
```

**Architecture Benefits**:
- Separation of concerns: CLI orchestrates, retrieval API searches, LLM generator answers
- Stateless HTTP client: CLI doesn't touch Milvus directly (avoids lock conflicts)
- Extensible: Easy to add features without changing core logic
- Reusable: LLM generator can be used by other components (API endpoints, batch jobs)

---

## Getting Started

### Prerequisites

- FastAPI server running on `http://localhost:8000`
- Chunks previously scraped and indexed (via `/api/v1/scrape` endpoint)
- Anthropic API key (for Claude Haiku access)

### Setup

1. **Add your Anthropic API key to `.env`**:
   ```bash
   echo "ANTHROPIC_API_KEY=sk-ant-YOUR_KEY_HERE" >> .env
   ```

2. **Install dependencies** (anthropic SDK already added via `uv add`):
   ```bash
   uv sync
   ```

### Running the CLI

```bash
# Run the CLI using uv
uv run cli.py

# Or run directly with Python
python cli.py
```

### Example Session

```
RAG Chatbot
Connected to http://localhost:8000
Type your query and press Enter. Type 'exit' or Ctrl+C to quit.
────────────────────────────────────────────────────────────

Query> what are some affordable travel guides?

  #1  [score: 0.87]  Budget Travel Guide to Europe
      £12.99  |  https://books.toscrape.com/catalogue/travel_book_1/...
      "Budget Travel Guide to Europe: This comprehensive guide covers..."

  #2  [score: 0.82]  Backpacking Through Asia
      £9.99  |  https://books.toscrape.com/catalogue/travel_book_2/...
      "Backpacking Through Asia: A budget traveler's handbook..."

  2 chunks retrieved.

Answer
────────────────────────────────────────────────────────────
Based on the retrieved guides, I can recommend two affordable travel options:

1. **Budget Travel Guide to Europe** (£12.99) - This comprehensive guide covers
   affordable travel across Europe, perfect for budget-conscious travelers.

2. **Backpacking Through Asia** (£9.99) - An excellent handbook for backpackers,
   offering practical advice for traveling through Asia on a limited budget.

Both are reasonably priced and specifically designed for travelers looking to
maximize their experience while minimizing costs.

Query> tell me more about the europe guide

  #1  [score: 0.91]  Budget Travel Guide to Europe
      £12.99  |  https://books.toscrape.com/catalogue/travel_book_1/...
      "Budget Travel Guide to Europe: Covers destinations like France, Italy..."

  #2  [score: 0.88]  Budget Travel Guide to Europe
      £12.99  |  https://books.toscrape.com/catalogue/travel_book_1/...
      "Budget Travel Guide to Europe: Money-saving tips for accommodations..."

  2 chunks retrieved.

Answer
────────────────────────────────────────────────────────────
The Budget Travel Guide to Europe provides practical information for budget
travelers exploring European destinations. It covers specific destinations like
France and Italy, along with valuable money-saving tips for accommodations.
Priced at £12.99, it's an affordable resource that helps travelers maximize
their budget while experiencing Europe fully.

Query> what is the price?

  #1  [score: 0.85]  Budget Travel Guide to Europe
      £12.99  |  https://books.toscrape.com/catalogue/travel_book_1/...
      "Budget Travel Guide to Europe is priced at £12.99..."

  1 chunk retrieved.

Answer
────────────────────────────────────────────────────────────
The Budget Travel Guide to Europe, which we've been discussing, is priced at
£12.99, making it quite affordable for travelers on a budget.

Query> exit
```

**Note**: In the example above, turn 2 ("tell me more about the europe guide") is automatically rewritten to "Budget Travel Guide to Europe features and content" before retrieval, which returns much more relevant chunks. Turn 3 ("what is the price?") is rewritten to include context about the Europe guide, and Claude naturally references prior answers.

---

## Usage

### Interactive Loop

The CLI operates as an interactive REPL with multi-turn conversation support:

1. **Startup**: Initializes Anthropic client, displays welcome message, connects to API
2. **Query Prompt**: `Query>` prompt appears, waiting for user input
3. **Input**: Type a natural language query (e.g., "affordable travel guides", "tell me more about that")
4. **Query Rewriting** (turn 2+): If conversation history exists, uses Claude Haiku to rewrite the query into a standalone query. For example, "tell me more about the europe guide" becomes "Budget Travel Guide to Europe features and content". First turn skips this step.
5. **Retrieval**: Top 5 chunks are fetched from the vector database using the (possibly rewritten) query
6. **Display Chunks**: Retrieved chunks displayed with scores and metadata
7. **LLM Response**: Claude Haiku generates an answer using chunks + conversation history as context, streamed to terminal
8. **History Storage**: Original query and answer are stored in memory for future context
9. **Loop**: Prompt appears again for the next query
10. **Exit**: Type `exit`, `quit`, or press `Ctrl+C` to quit gracefully

### Output Format

**Chunks Section**:
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

**LLM Answer Section**:
```
Answer
────────────────────────────────────────────────────────────
[Claude Haiku's streamed response based on the chunks]
```

### Entering Queries

```bash
Query> what are the best programming books?
Query> tell me about python tutorials
Query> show me travel guides under 20 pounds
Query> [empty line] → ignored, re-prompts
Query> exit → gracefully exits
Query> quit → gracefully exits
Query> [Ctrl+C] → gracefully exits
```

**Query Tips**:
- Use natural language (the embedding model understands semantics)
- Longer, more specific queries yield more relevant results
- Follow-up questions like "tell me more" work naturally due to query rewriting
- If no chunks are found, no LLM call is made (avoids wasted API calls)
- Empty input is ignored (no error, just re-prompts)
- Queries are case-insensitive
- Conversation history is stored in-memory and cleared when you exit the CLI

---

## Configuration

### API Endpoint

The CLI connects to `http://localhost:8000` by default. To use a different endpoint, update `config/config.py`:

```python
api_base_url: str = "http://your-api-server:8000"
```

Or set the environment variable:
```bash
export API_BASE_URL="http://your-api-server:8000"
```

### Anthropic API Key

Required for LLM response generation. Set via `.env`:

```bash
ANTHROPIC_API_KEY=sk-ant-YOUR_KEY_HERE
```

Or set the environment variable:
```bash
export ANTHROPIC_API_KEY="sk-ant-YOUR_KEY_HERE"
```

### Default Parameters

The CLI uses these fixed defaults:

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `top_k` | `5` | Number of chunks to retrieve |
| `model` | `claude-haiku-4-5-20251001` | Claude Haiku model for answers |
| `max_tokens` | `512` | Maximum tokens in LLM response |
| `rewrite_max_tokens` | `128` | Maximum tokens for query rewriting (turn 2+) |
| `timeout` | `10.0s` | HTTP request timeout |

To modify these, edit:
- `retrieve()` function in `cli.py` for retrieval parameters
- `rewrite_query()` method in `src/llm/generator.py` for query rewriting
- `generate()` method in `src/llm/generator.py` for answer generation

**Note on Performance**: Query rewriting adds a small latency on turns 2+ (typically 0.5–1s) since it requires an extra LLM call to Anthropic. Turn 1 has no rewriting overhead.

---

## Implementation Details

### Retrieval Process

The CLI calls the existing `/api/v1/retrieve` endpoint, which handles:
- Query validation (non-empty string)
- Embedding generation (SentenceTransformer)
- Vector similarity search (Milvus)
- Result ranking (by cosine similarity score)

See [retrieval.md](retrieval.md) for endpoint details.

### LLM Answer Generation

The `AnswerGenerator` class (`src/llm/generator.py`) has two methods:

**`rewrite_query(query, history)` — Query Rewriting (Turn 2+)**:
1. Called only when conversation history exists (skipped on turn 1)
2. Takes the user's raw follow-up query and conversation history
3. Makes a cheap LLM call (max 128 tokens) to rewrite the query as a standalone search query
4. Example: "tell me more about the europe guide" → "Budget Travel Guide to Europe features and content"
5. The rewritten query is used for retrieval (better vector search results)
6. Returns the original query if rewriting fails

**`generate(query, chunks, history=None)` — Answer Generation**:
1. Takes an Anthropic client and initializes once at CLI startup
2. Receives the original query, retrieved chunks, and optional conversation history
3. Builds a context string from chunks (title + text for each)
4. Constructs messages list: `[history turns] + [current turn with chunks]`
5. Calls Claude Haiku with system prompt and full conversation context
6. Streams the response word-by-word to terminal
7. Returns the full answer text as a string (for storage in history)
8. Only runs if chunks are found (no wasted API calls on empty results)

**System Prompt**:
> "You are a helpful assistant. Answer the user's question using only the provided context. If the context does not contain enough information, say so. When the user refers to something mentioned earlier in the conversation, use the conversation history to resolve the reference."

### Conversation History

The CLI maintains an in-memory list of conversation turns:
- Each turn is a dict: `{"role": "user"|"assistant", "content": "..."}` 
- Only plain Q&A is stored — chunk context is never added to history
- History grows by 2 entries (user + assistant) per successful turn
- History is passed to the LLM so Claude can reference prior answers
- History is stored only when chunks are found and LLM generates an answer

### Error Handling

The CLI gracefully handles common errors:

| Error | Behavior |
|-------|----------|
| **API unreachable** | Displays error message, re-prompts for next query |
| **Invalid query** | API returns 400, error shown, re-prompts |
| **No chunks found** | Displays "No chunks found.", skips LLM call, re-prompts |
| **Anthropic API error** | Shows error, re-prompts (LLM still attempted) |
| **Keyboard interrupt (Ctrl+C)** | Exits cleanly with newline |
| **EOF (e.g., piped input)** | Exits cleanly |

### HTTP Timeout

Retrieval requests have a 10-second timeout. If the API takes longer:
```
Error: operation timed out after 10.0 seconds
```

For slow networks or large collections, increase the timeout in the `retrieve()` function.

---

## File Structure

```
src/llm/
├── __init__.py           # Exports AnswerGenerator
└── generator.py          # AnswerGenerator class with generate() method

cli.py                    # Main CLI entry point
config/config.py          # Settings including anthropic_api_key
```

---

## Multi-Turn Conversation Behavior

### How It Works

The chatbot maintains conversation history across turns to enable natural multi-turn interactions:

1. **Turn 1**: User asks a question → retrieved directly → answer stored in history
2. **Turn 2+**: User asks a follow-up → query is rewritten → retrieval happens on the rewritten query → answer references history

### Query Rewriting

On turns 2 and beyond, vague follow-up questions are automatically rewritten before retrieval:

| User Input | Rewritten Query (for retrieval) |
|------------|--------------------------------|
| "tell me more about the europe guide" | "Budget Travel Guide to Europe features and content" |
| "what is the price?" | "Budget Travel Guide to Europe price cost GBP" |
| "does it cover france?" | "Budget Travel Guide to Europe france destinations coverage" |

The original user input is stored in history (natural phrasing), but the rewritten query improves vector search.

### History Storage & Limits

- History is stored **in-memory only** and is cleared when you exit the CLI
- History grows by 2 entries (user + assistant) per successful turn
- No artificial truncation is applied (Haiku has a 200k token context window)
- History is only appended when `generate()` actually runs (if chunks are found)
- If retrieval returns no chunks, that turn is skipped and not added to history

### When History Helps

Multi-turn conversation is most effective for:
- Asking follow-ups to refine previous answers ("tell me more about", "what about")
- Asking related questions that reference prior context ("what's the price of that book?")
- Building on previous queries in the same session
- Natural conversational flow without re-stating the full context each time

### Limitations

- History is **not persisted** between sessions (restarting the CLI clears history)
- Query rewriting adds ~0.5–1s latency on turns 2+ (extra LLM API call)
- If history becomes very long (100+ turns), token usage increases linearly
- The original user query must still be reasonably clear for rewriting to work well

---

## Troubleshooting

### Missing `ANTHROPIC_API_KEY`

**Error**: `anthropic_api_key` field required

**Cause**: API key not set in `.env` or environment variable

**Solution**:
```bash
echo "ANTHROPIC_API_KEY=sk-ant-YOUR_KEY_HERE" >> .env
```

Then restart the CLI.

### "Connected to http://localhost:8000" but no chunks

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
3. Check the `api_base_url` in `config/config.py` matches your server

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

### "No module named httpx" or "No module named anthropic"

**Solution**: Ensure your virtual environment is activated:

```bash
uv run cli.py
```

---

## Code Reference

### Entry Point

**File**: `cli.py` at project root

**Key Functions**:

```python
def retrieve(query: str, top_k: int = 5) -> list[dict]:
    """Calls /api/v1/retrieve via HTTP, returns chunks."""

def display_chunks(chunks: list[dict]) -> None:
    """Formats and prints chunks to terminal."""

def main() -> None:
    """Runs the interactive REPL loop with multi-turn conversation support.
    
    Maintains an in-memory history list of {role, content} dicts.
    For turn 2+, calls generator.rewrite_query() before retrieval.
    Passes history to generator.generate() and stores the response.
    """
```

### LLM Generator

**File**: `src/llm/generator.py`

**Class**: `AnswerGenerator`

```python
class AnswerGenerator:
    def __init__(self, client: anthropic.Anthropic):
        """Initialize with an Anthropic client."""
        
    def rewrite_query(self, query: str, history: list[dict]) -> str:
        """Rewrite a follow-up query into a standalone query using conversation history.
        
        Only called when history exists (turn 2+). Returns the rewritten query
        or the original query if rewriting fails.
        """
        
    def generate(self, query: str, chunks: list[dict], history: list[dict] | None = None) -> str:
        """Generate an LLM answer based on retrieved chunks and conversation history.
        
        Returns the full answer text as a string (for storage in history).
        history is optional and defaults to None.
        """
```

### Dependencies

- `anthropic>=0.52.0` - Anthropic SDK for Claude API access
- `httpx>=0.28.1` - HTTP client for API calls
- Other dependencies in `pyproject.toml`

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

### Ask About Book Recommendations

```bash
Query> recommend affordable travel books

  #1  [score: 0.89]  Budget Travel Guide to Europe
      £12.99  |  https://books.toscrape.com/catalogue/budget_guide_europe/...
      "Budget Travel Guide to Europe: This comprehensive guide covers..."

  #2  [score: 0.87]  Backpacking Through Southeast Asia
      £9.99  |  https://books.toscrape.com/catalogue/backpack_asia/...
      "Backpacking Through Southeast Asia: A practical guide for budget..."

  2 chunks retrieved.

Answer
────────────────────────────────────────────────────────────
Based on the retrieved books, I recommend:

1. **Budget Travel Guide to Europe** (£12.99) - A comprehensive guide to
   traveling affordably across Europe, covering multiple destinations and
   money-saving strategies.

2. **Backpacking Through Southeast Asia** (£9.99) - An excellent, affordable
   guide specifically for budget backpackers traveling through Southeast Asia,
   with practical on-the-ground advice.

Both are reasonably priced and tailored for travelers on a budget.
```

### Get Programming Help

```bash
Query> how do I learn python programming?

  #1  [score: 0.93]  Python Crash Course
      £28.99  |  https://books.toscrape.com/catalogue/python-crash/...
      "Python Crash Course: Learn Python by doing with hands-on projects..."

  #2  [score: 0.89]  Automate the Boring Stuff with Python
      £24.95  |  https://books.toscrape.com/catalogue/automate/...
      "A practical guide to automating everyday tasks with Python..."

  2 chunks retrieved.

Answer
────────────────────────────────────────────────────────────
Based on available resources, here are two excellent ways to learn Python:

1. **Python Crash Course** (£28.99) - Perfect for beginners, this book teaches
   Python through hands-on projects, helping you learn by doing.

2. **Automate the Boring Stuff with Python** (£24.95) - A practical guide that
   shows you how to use Python to automate real-world tasks, making learning
   immediately applicable.

Both are well-regarded resources for learning Python effectively.
```

### Empty Results Handling

```bash
Query> quantum entanglement physics

  No chunks found.

Query> [No LLM call made, as there's no context to work with]
```

---

## Comparison with Swagger UI

| Feature | Swagger UI | CLI |
|---------|-----------|-----|
| **Access** | Browser-based | Terminal-based |
| **Query Speed** | Slower (UI overhead) | Faster (direct HTTP) |
| **Batch Queries** | One at a time | Multiple (REPL loop) |
| **Ease of Use** | Visual forms | Type directly |
| **LLM Answers** | No | Yes (Claude Haiku) |
| **Streaming** | No | Yes (word-by-word) |
| **Ideal For** | API exploration | Interactive chatbot |

---

## Contributing

To extend the CLI:
1. Edit `cli.py` at the project root for:
   - REPL loop changes (input handling, history management)
   - Retrieval orchestration
   - Display formatting
2. Edit `src/llm/generator.py` for:
   - LLM behavior changes (system prompts, models)
   - Query rewriting logic (`rewrite_query()`)
   - Answer generation logic (`generate()`)
3. Keep concerns separated: retrieval, display, generation, and history management
4. Test with `uv run cli.py` - verify both single-turn (turn 1) and multi-turn (turn 2+) behavior

### Common Customizations

- **Change the answer model**: Edit `model=` in both `rewrite_query()` and `generate()` methods
- **Change max tokens**: Edit `max_tokens=` parameters in `src/llm/generator.py`
- **Change system prompt**: Edit the `system=` parameter in `generate()` method
- **Disable query rewriting**: Remove the `if history:` block in `cli.py` main loop
- **Add persistent history**: Save/load history from a file before/after the REPL loop

For bug reports or feature requests, see the project's contribution guidelines.
