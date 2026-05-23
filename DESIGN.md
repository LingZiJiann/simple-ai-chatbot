# System Design: RAG Chatbot

## ⚠️ Disclaimer

This project is a **demonstration/proof-of-concept RAG system** designed for educational purposes. The web scraper is configured to work **exclusively with [books.toscrape.com](https://books.toscrape.com)**, a website specifically designed for practicing web scraping techniques.

---

## Overview

This document outlines the architecture, prompt engineering approach, and data retrieval strategy for a Retrieval-Augmented Generation (RAG) chatbot system that combines web scraping, semantic search, and LLM-powered response generation.

The system enables users to query a web-indexed knowledge base through a conversational interface, with the chatbot providing contextually relevant answers grounded in retrieved content.

---

## 1. Overall Architecture

### System Components

The system consists of four primary layers:

```
┌─────────────────────────────────────────────────────────┐
│                   CLI (User Interface)                   │
│                   ├─ Interactive REPL                    │
│                   ├─ Query input/output                  │
│                   └─ Conversation history management     │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────┴──────────────────────────────────┐
│            API Layer (FastAPI Server)                    │
│  ┌─────────────────────────────────────────────────────┐ │
│  │ /api/v1/scrape     → Web scraping & chunking       │ │
│  │ /api/v1/retrieve   → Semantic search               │ │
│  └─────────────────────────────────────────────────────┘ │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────┴──────────────────────────────────┐
│        Data Processing & ML Layer                        │
│  ┌─────────────────────────────────────────────────────┐ │
│  │ Scraper         → Extract pages & metadata         │ │
│  │ Chunker         → Segment content semantically     │ │
│  │ Embedder        → Generate dense vectors           │ │
│  │ LLM Generator   → Query rewriting & answering      │ │
│  └─────────────────────────────────────────────────────┘ │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────┴──────────────────────────────────┐
│            Storage Layer                                 │
│  ├─ Milvus Vector Database (embeddings)               │
│  └─ Configuration & Metadata                            │
└──────────────────────────────────────────────────────────┘
```

### Data Flow: Complete Pipeline

```
User Query (Terminal)
    ↓
[CLI] ┌─ Turn 1: Skip query rewriting
      └─ Turn 2+: Rewrite query using Claude Haiku (cheap LLM call, max 128 tokens)
    ↓
[HTTP POST /api/v1/retrieve] → API Server
    ↓
[Embedder] Encode query to 384-dim vector (SentenceTransformer)
    ↓
[Milvus] Cosine similarity search for top K chunks
    ↓
[Retrieved Chunks] With metadata (title, URL, price, similarity scores)
    ↓
[Validate Relevance] Chunks inspected for debugging/validation (internal only)
    ↓
[Claude Haiku] Generate answer using chunks + conversation history
    ↓
[Stream Answer] Word-by-word to terminal
    ↓
[Store in History] Original query + answer for future context
    ↓
[Next Query] Loop repeats
```

---

## 2. Prompt Engineering Choices

### 2.1 Query Rewriting (Multi-Turn Conversation Support)

**Problem**: Follow-up questions like "tell me more about that" lack sufficient context for effective semantic search.

**Solution**: Use Claude Haiku to rewrite vague follow-ups into standalone, contextual queries before retrieval.

#### Implementation

**When**: Only on turns 2+ (turn 1 skips rewriting to avoid latency)

**Cost**: Single LLM call per follow-up (max 128 tokens generation)

**Example Transformations**:

| User Input | Rewritten Query |
|---|---|
| "tell me more about the europe guide" | "Budget Travel Guide to Europe features and content" |
| "what is the price?" | "Budget Travel Guide to Europe price cost GBP" |
| "does it cover france?" | "Budget Travel Guide to Europe france destinations coverage" |

**Prompt Design**:
```
System: You are a query rewriting assistant. Given a user's follow-up question 
and conversation history, rewrite the question as a standalone search query 
suitable for semantic search. The rewritten query should:
- Include key terms from the conversation history
- Be specific and self-contained
- Include search-relevant keywords
- Be concise (under 20 words)

Return only the rewritten query, no explanation.
```

**Rationale**:
- Improves vector search recall by adding explicit context
- Leverages conversation history without storing full context in retrieval
- Minimal token cost (max 128 tokens) for significant UX improvement

### 2.2 Answer Generation (Grounded Response)

**Problem**: LLMs can hallucinate; answers must be grounded in retrieved content and conversation history.

**Solution**: Provide retrieved chunks as context alongside conversation history.

#### Implementation

**Model**: Claude Haiku (fast, cost-efficient, sufficient for grounding)

**Max Tokens**: 512 (sufficient for detailed answers without verbosity)

**Context Provided**:
1. Conversation history (all prior turns)
2. Retrieved chunks (top 5 by similarity score)
3. Original user query

**System Prompt**:
```
You are a helpful assistant. Answer the user's question using only the provided 
context. If the context does not contain enough information, say so. When the 
user refers to something mentioned earlier in the conversation, use the 
conversation history to resolve the reference.
```

**Message Structure**:
```
[
  {"role": "user", "content": "first question"},
  {"role": "assistant", "content": "first answer"},
  ...
  {"role": "user", "content": f"<chunks>\n{chunk_context}\n</chunks>\n\n{current_query}"}
]
```

**Rationale**:
- **Grounding**: Chunks act as the ground truth for answers
- **History**: Prior answers provide context for reference resolution
- **Safety**: System prompt explicitly prevents hallucination
- **Cost**: Haiku is 10x cheaper than Opus while sufficient for grounding

### 2.3 No Query Rewriting on Turn 1

**Decision**: Skip rewriting on the first turn to minimize latency.

**Rationale**:
- First turn has no conversation history to rewrite from
- Users typically formulate first queries more carefully than follow-ups
- Saves 500-1000ms of latency (one LLM call)
- Turn 1 vectors space searches are often sufficient

---

## 3. Data Retrieval Strategy

### 3.1 Chunking Strategy

**Rationale**: Without chunking, entire pages would be single embeddings—causing poor retrieval precision (a query matches only if the whole page is relevant) and diluted semantic meaning. Chunking breaks pages into focused units, improving both retrieval accuracy and embedding quality.

**Goal**: Segment content into semantic units suitable for embedding and retrieval.

#### Chunking Parameters

| Parameter | Value | Rationale |
|---|---|---|
| **Min Length** | 200 chars | Provides sufficient semantic content |
| **Max Length** | 500 chars | Fits well in 384-dim embeddings; balances specificity |
| **Strategy** | Paragraph-first, sentence fallback | Respects semantic boundaries |

#### Chunk Metadata

Each chunk preserves:
- **chunk_id**: 16-char hash of URL + chunk index (unique identifier)
- **source_url**: Original page URL (for attribution)
- **chunk_index**: Sequential index within page (for ordering)
- **text**: Combined title + content excerpt
- **char_count**: Original character count (before truncation)
- **page_title**: Source page title
- **price_gbp**: Product price (if available; null otherwise)

### 3.2 Embedding Generation

**Embedding Model**: `paraphrase-MiniLM-L6-v2` (Hugging Face)

#### Model Selection Rationale

| Criterion | Choice | Why |
|---|---|---|
| **Inference Speed** | MiniLM | < 100ms on CPU; suitable for real-time queries |
| **Dimensionality** | 384 | Semantic richness + memory efficiency trade-off |
| **Language Support** | 50+ languages | Supports diverse content |
| **Benchmark** | MTEB 58.89 | Strong semantic understanding |
| **Model Size** | 22M params | Low resource overhead |

#### Embedding Process

```
For each chunk:
  1. Extract text content
  2. Encode using SentenceTransformer (non-trainable, deterministic)
  3. Convert PyTorch tensor to Python list (Milvus format)
  4. Normalize: cap text at 1024 chars, title at 512 chars
  5. Handle nulls: price -1.0 sentinel for missing values
  6. Upsert into Milvus collection (insert or update)
```

### 3.3 Vector Storage (Milvus)

**Database**: Milvus Lite (embedded, file-based)

**Rationale**: Lightweight and fast performance for POC development without infrastructure overhead. Supports required retrieval methods like cosine similarity, enabling rapid iteration with the ability to scale to Milvus Server later if needed.

#### Collection Schema

```
Collection: "chunks" (or configurable name)

Fields:
  - chunk_id (VARCHAR, primary key, unique)
  - source_url (VARCHAR)
  - chunk_index (INT64)
  - text (VARCHAR, max 1024 chars)
  - char_count (INT64)
  - page_title (VARCHAR, max 512 chars)
  - price_gbp (FLOAT, -1.0 = null)
  - vector (FLOAT_VECTOR, dim=384, indexed)

Index:
  - Type: FLAT (exhaustive search for exact results)
  - Metric: COSINE (normalized L2 distance)
  - Default_index: true
```

### 3.4 Semantic Search (Retrieval Process)

**Endpoint**: `POST /api/v1/retrieve`

**Request**:
```json
{
  "query": "affordable travel guides",
  "top_k": 5
}
```

**Process**:

```
1. Validate input (top_k ∈ [1, 20], non-empty query)
2. Encode query to 384-dim vector (same SentenceTransformer)
3. Search Milvus for top K nearest neighbors (cosine distance)
4. Retrieve chunk metadata alongside distance scores
5. Normalize distances to scores: score = max(0, (1 + cosine_distance) / 2)
6. Handle nulls: restore price_gbp from -1.0 sentinel to None
7. Return ranked results (highest score first)
```

**Response**:
```json
{
  "query": "affordable travel guides",
  "results": [
    {
      "chunk_id": "a1b2c3d4e5f6g7h8",
      "source_url": "https://example.com/...",
      "chunk_index": 0,
      "text": "Budget Travel Guide to Europe: ...",
      "char_count": 245,
      "page_title": "Budget Travel Guide to Europe",
      "price_gbp": 12.99,
      "score": 0.87
    },
    ...
  ]
}
```

#### Performance Characteristics

| Operation | Latency | Bottleneck |
|---|---|---|
| Query Encoding | 50-100ms | Transformer inference |
| Vector Search (FLAT, 100K vectors) | 10-50ms | Linear scan |
| Metadata Retrieval | < 5ms | Database lookup |
| **Total** | **~100-150ms** | Embedding model |

**Scaling to 1M+ vectors**: Switch to IVF or HNSW index (10-50ms search)

---

## 4. Integration Points

### 4.1 Web Scraping → Vector Storage

```
Scraper extracts pages
    ↓
[/api/v1/scrape endpoint] returns chunks
    ↓
[scraper/router.py] calls vectorstore.upsert_chunks()
    ↓
[Chunks embedded and indexed in Milvus]
    ↓
[Immediately searchable via /api/v1/retrieve]
```

**Key**: Chunks are automatically embedded and indexed; no separate indexing step.

### 4.2 Retrieval → LLM Grounding

```
[/api/v1/retrieve] returns top_k chunks
    ↓
[CLI displays chunks]
    ↓
[chunks passed to AnswerGenerator.generate()]
    ↓
[Claude Haiku receives chunks + history]
    ↓
[Grounds answer in retrieved context]
```

**Key**: Retrieved chunks are the authoritative source for answer generation.

### 4.3 Multi-Turn Conversation Loop

```
Turn 1:
  Query → Embed & Search → Retrieve Chunks → Generate Answer → Store in History

Turn 2+:
  Query → Rewrite (using history) → Embed & Search → Retrieve Chunks → 
  Generate Answer (with history) → Store in History
```

**Key**: Query rewriting happens before embedding; history used for rewriting AND answering.

---

## 5. Design Decisions & Trade-offs

### 5.1 Model Choices

Claude Haiku is used for both query rewriting and answer generation because simple tasks like query transformation and grounded answering are less likely to hallucinate with a focused, smaller model. paraphrase-MiniLM-L6-v2 provides fast, efficient embeddings, and FLAT indexing ensures exact retrieval results suitable for current scale.

---

## Appendix: File Structure

```
src/
├── scraper/
│   ├── scraper.py          # Breadth-first crawler
│   ├── chunker.py          # Content segmentation
│   ├── embedder.py         # Text-to-vector conversion
│   ├── router.py           # /api/v1/scrape endpoint
│   └── schemas.py          # Pydantic request/response models

├── retrieval/
│   ├── router.py           # /api/v1/retrieve endpoint
│   └── schemas.py          # Search request/response schemas

├── vectorstore/
│   └── store.py            # Milvus integration

├── llm/
│   └── generator.py        # Query rewriting & answer generation

└── utils/
    ├── config.py           # Configuration management
    └── logger.py           # Logging setup

cli.py                       # User-facing CLI interface
main.py                      # FastAPI application entry point

config/
└── config.py               # Settings (milvus_db_path, etc.)

docs/
├── web_scrape.md          # Scraping & chunking guide
├── retrieval.md           # Vector search guide
└── cli.md                 # CLI usage guide
```
