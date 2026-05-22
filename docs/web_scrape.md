# Web Scraping & Chunking Documentation

## Overview

The web scraping module provides a FastAPI-based service for crawling websites, extracting structured product information, automatically chunking content, and converting chunks into embeddings for vector-based semantic search.

The complete pipeline includes:
1. **Web Scraping**: Breadth-first crawling of websites with politeness controls
2. **Chunking**: Semantic segmentation of extracted content into manageable pieces
3. **Embedding**: Conversion of chunks into vector embeddings using a language model
4. **Vector Storage**: Persistent storage in Milvus vector database for fast similarity search

The system performs breadth-first crawling with respect for server resources through politeness delays and domain-level rate limiting.

---

## Architecture

### Components

1. **Scraper** (`scraper.py`) - Core crawling logic
2. **Router** (`router.py`) - FastAPI endpoint definitions
3. **Chunker** (`chunker.py`) - Content segmentation
4. **Embedder** (`embedder.py`) - Chunk-to-embedding conversion using language models
5. **Vector Store** (`vectorstore/store.py`) - Milvus integration for vector persistence
6. **Schemas** (`schemas.py`) - Pydantic data models

---

## Core Concepts

### Crawling Strategy

- **Breadth-First Search (BFS)**: Explores pages level-by-level from a seed URL
- **Domain Isolation**: Only crawls internal links within the seed domain
- **Depth Control**: Limits how many link hops away from the seed URL to traverse
- **Page Limit**: Respects a maximum page count to prevent runaway crawls

### Politeness & Rate Limiting

- **Per-Domain Locks**: Ensures sequential requests to the same domain
- **Politeness Delay**: Configurable delay between requests (default in config)
- **Retry Logic**: Automatic retries with exponential backoff for transient failures
- **User-Agent**: Custom User-Agent header to identify the crawler

### Data Extraction

Each page yields:
- **Title**: From `<title>` tag, falling back to `<h1>` or URL
- **Product Description**: Text from `<div id="product_description">` next sibling `<p>`
- **Price**: Numeric value extracted from `<div class="product_price">` → `<p class="price_color">`
- **Raw HTML**: Full page HTML for archival or re-processing

### Chunking

Content is split into semantic chunks within size bounds:
- **Minimum**: 200 characters per chunk
- **Maximum**: 500 characters per chunk
- **Strategy**: Prefer paragraph breaks, fall back to sentence boundaries

Each chunk includes metadata for traceability:
- Unique chunk ID (SHA256 hash of URL + index)
- Source URL
- Page title
- Price (if available)

### Embedding & Vector Storage

After chunking, each chunk is converted into a dense vector embedding:
- **Embedding Model**: Uses a language model to generate semantic embeddings
- **Vector Dimension**: Fixed-size dense vectors enabling similarity search
- **Metadata Preservation**: Original chunk metadata (URL, title, price) attached to each embedding
- **Vector Database**: Embeddings stored in Milvus for efficient approximate nearest-neighbor search

This enables semantic search capabilities where users can find relevant content based on meaning rather than keyword matching.

---

## API Endpoint

### `POST /scrape`

Scrape and chunk a website.

#### Request Schema

```json
{
  "url": "https://books.toscrape.com/catalogue/category/books/travel_2/index.html",
  "depth": 2,
  "max_pages": 5,
  "link_pattern": "^/catalogue/(?!category)"
}
```

| Field | Type | Default | Constraints | Description |
|-------|------|---------|-------------|-------------|
| `url` | `str` | `https://books.toscrape.com/catalogue/category/books/travel_2/index.html` | - | Seed URL to start crawling from |
| `depth` | `int` | `2` | `0 ≤ depth ≤ 10` | Maximum link hops from seed URL |
| `max_pages` | `int` | `5` | `1 ≤ max_pages ≤ 500` | Maximum pages to crawl before stopping |
| `link_pattern` | `str \| null` | `^/catalogue/(?!category)` | Valid regex | Optional regex to filter discovered links by URL path |

#### Response Schema

```json
{
  "seed_url": "https://books.toscrape.com/catalogue/category/books/travel_2/index.html",
  "pages_crawled": 5,
  "chunks": [
    {
      "chunk_id": "a1b2c3d4e5f6g7h8",
      "source_url": "https://books.toscrape.com/catalogue/travel_book_1/index.html",
      "chunk_index": 0,
      "text": "Book Title: This is a fascinating travel guide...",
      "char_count": 245,
      "page_title": "Book Title",
      "price_gbp": 12.99
    }
  ]
}
```

| Field | Type | Description |
|-------|------|-------------|
| `seed_url` | `str` | The original seed URL provided in the request |
| `pages_crawled` | `int` | Total number of pages successfully crawled |
| `chunks` | `Chunk[]` | List of extracted and chunked content |

#### Chunk Schema Details

| Field | Type | Description |
|-------|------|-------------|
| `chunk_id` | `str` | 16-character hash derived from source URL and chunk index |
| `source_url` | `str` | Full URL of the page this chunk came from |
| `chunk_index` | `int` | Sequential index of this chunk within its page |
| `text` | `str` | Combined page title and description fragment |
| `char_count` | `int` | Character count of the chunk text |
| `page_title` | `str` | Title of the source page |
| `price_gbp` | `float \| null` | Product price in GBP, if present on the page |

#### Example Usage

```bash
curl -X POST http://localhost:8000/scrape \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://books.toscrape.com",
    "depth": 1,
    "max_pages": 10
  }'
```

---

## Vector Store Integration

After chunks are extracted via `/scrape`, they can be converted to embeddings and stored in Milvus for semantic search.

### Embedding Pipeline

The embedding pipeline accepts the chunks from the scraper and:
1. Generates vector embeddings for each chunk using a language model
2. Stores the embeddings in the Milvus vector database
3. Maintains chunk metadata alongside the vectors for result attribution
4. Enables fast approximate nearest-neighbor search for semantic queries

### Vector Database (Milvus)

**Milvus** is an open-source vector database optimized for:
- High-dimensional vector similarity search
- Low-latency queries across millions of vectors
- Horizontal scalability

Embeddings are indexed in Milvus with:
- Chunk text embeddings (primary search key)
- Chunk metadata (source URL, page title, price)
- Unique chunk IDs for traceability

### Usage

Scraped chunks are automatically converted to embeddings and stored in Milvus, making them searchable via vector similarity queries (e.g., "find chunks similar to this query").

---

## Error Handling

### Crawl Failures

If the crawl operation fails with an unexpected error, the endpoint returns:

```json
{
  "detail": "Crawl failed: [error message]"
}
```

HTTP Status: **500 Internal Server Error**

### Per-Page Failures

Individual page fetch failures are logged as warnings but do not halt the crawl. The crawler will continue with the next URL in the queue.

### Transient Network Errors

Network failures (transport errors, timeouts) trigger automatic retries:
- **Max Retries**: Configurable (default from `config.settings.scraper_max_retries`)
- **Backoff**: Random wait between `scraper_retry_min_wait` and `scraper_retry_max_wait`

---

## Configuration

Configuration is loaded from `config/config.py` and can be overridden via environment variables:

| Setting | Default | Purpose |
|---------|---------|---------|
| `scraper_user_agent` | Custom User-Agent | HTTP header to identify the crawler |
| `scraper_request_timeout` | (from config) | Timeout for individual HTTP requests |
| `scraper_politeness_delay` | (from config) | Delay between requests to the same domain (seconds) |
| `scraper_max_retries` | (from config) | Maximum retry attempts on transient failures |
| `scraper_retry_min_wait` | (from config) | Minimum backoff wait time (seconds) |
| `scraper_retry_max_wait` | (from config) | Maximum backoff wait time (seconds) |

---

## Usage Examples

### Basic Crawl

Crawl a website up to depth 2, extracting up to 10 pages:

```python
import httpx
from src.scraper.scraper import crawl

pages = await crawl(
    seed_url="https://example.com",
    depth=2,
    max_pages=10
)
```

### With Link Pattern Filtering

Only crawl URLs matching a specific path pattern:

```python
pages = await crawl(
    seed_url="https://example.com/products",
    depth=1,
    max_pages=50,
    link_pattern=r"^/products/(?!filter)"
)
```

### Via API

```python
import httpx

async with httpx.AsyncClient() as client:
    response = await client.post(
        "http://localhost:8000/scrape",
        json={
            "url": "https://example.com",
            "depth": 2,
            "max_pages": 20,
            "link_pattern": r"^/items"
        }
    )
    result = response.json()
    print(f"Crawled {result['pages_crawled']} pages into {len(result['chunks'])} chunks")
```

---

## Implementation Details

### URL Normalization

URLs are canonicalized to prevent duplicate crawling:
- Scheme and domain lowercased
- Fragments removed
- Trailing slashes normalized
- Query parameters preserved

### Data Extraction Logic

**Title Selection**:
1. `<title>` tag (preferred)
2. `<h1>` tag (fallback)
3. Page URL (last resort)

**Description**:
- Looks for `<div id="product_description">` followed by a `<p>` tag
- Returns empty string if not found

**Price**:
- Searches for `<div class="product_price">` → `<p class="price_color">`
- Extracts numeric value (handles currency symbols)
- Returns as float; `null` if not found

### Chunking Algorithm

1. Split text by paragraph breaks (`\n\n`) if multiple paragraphs exist
2. Fall back to sentence boundaries (`[.!?]`) if single paragraph
3. Greedily accumulate fragments while respecting size constraints
4. When adding a fragment would exceed `MAX_CHARS`, flush the buffer and start fresh

This approach preserves semantic boundaries while maintaining consistent chunk sizes.

---

## Logging

The module logs at several levels:

- **INFO**: Successful crawls and page extraction
- **WARNING**: Individual page fetch failures (non-fatal)
- **ERROR**: Critical crawl failures

Log messages include:
- Crawl progress (current depth/max depth, URL)
- Fetch failures with exception details
- Completion summary (pages crawled, seed URL)

Access logs via the `scraper` logger:

```python
from src.utils.logger import get_logger
logger = get_logger("scraper")
```

---

## Performance Considerations

### Crawl Speed

- **Politeness Delay**: Intentional delays respect server resources; adjust if needed
- **Max Pages**: Limits memory usage and crawl time
- **Depth**: Exponential explosion of URLs; keep depth low (0-3 recommended)

### Memory

- **Visited Set**: Stores normalized URLs; scales with pages crawled
- **Queue**: BFS queue size depends on site structure and depth
- **HTML Storage**: Raw HTML stored in results; consider downstream cleanup

### Concurrency

- Per-domain locks ensure sequential processing
- Multiple domains can be crawled in parallel
- Consider the site's capacity before tuning politeness delays

---

## Troubleshooting

### Empty Results

**Symptom**: `pages_crawled: 0` or minimal chunks

**Causes**:
- Seed URL unreachable or returns non-200 status
- Link pattern regex too restrictive
- Depth or max_pages too low

**Solution**: Verify URL is accessible, review link pattern, increase limits

### Missing Product Data

**Symptom**: Empty `prod_desc` or `price_gbp: null`

**Causes**:
- Expected HTML elements not found (div IDs, classes changed)
- Price not in expected format

**Solution**: Inspect target site's HTML structure; update selectors if needed

### Slow Crawls

**Symptom**: Crawl takes unexpectedly long

**Causes**:
- High `scraper_politeness_delay`
- Slow target server
- Many retries due to transient errors

**Solution**: Review logs for retry patterns; consider lower politeness delay if appropriate

### Timeouts

**Symptom**: `httpx.TimeoutException`

**Causes**:
- Target server slow or unresponsive
- Network latency
- Timeout value too low

**Solution**: Increase `scraper_request_timeout` or adjust retry strategy

---

## Future Enhancements

- **JavaScript Rendering**: Use Selenium/Playwright for JS-heavy sites
- **Caching**: LRU cache for repeated URLs
- **Structured Data**: Extract JSON-LD, microdata
- **Content Deduplication**: Identify and merge similar chunks based on embedding similarity
- **Proxy Support**: Rotate proxies for large crawls
- **Multi-Modal Embeddings**: Support image and document embedding models
- **Vector Search API**: Expose semantic search endpoints for querying embeddings
