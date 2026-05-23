# Simple AI Chatbot - RAG System

A Retrieval-Augmented Generation (RAG) chatbot that combines web scraping, semantic search, and Claude LLM to provide contextually relevant answers grounded in indexed web content.

## Features

- **Web Scraping & Indexing**: Scrape web content and automatically embed it into a vector database
- **Semantic Search**: Find relevant content chunks using sentence embeddings
- **LLM-Powered Responses**: Generate answers grounded in retrieved context using Claude
- **Multi-turn Conversations**: Support for follow-up questions with automatic query rewriting
- **FastAPI Backend**: RESTful API for scraping and retrieval
- **Interactive CLI**: User-friendly command-line interface

## System Architecture

```
┌─────────────────────────────┐
│   CLI (Interactive REPL)    │
└──────────────┬──────────────┘
               │
┌──────────────┴──────────────┐
│     FastAPI Server          │
│  /api/v1/scrape             │
│  /api/v1/retrieve           │
└──────────────┬──────────────┘
               │
┌──────────────┴──────────────────────┐
│  Processing Layer                   │
│  - Web Scraper (BeautifulSoup)      │
│  - Content Chunker                  │
│  - Embedder (SentenceTransformer)   │
│  - LLM Generator (Claude)           │
└──────────────┬──────────────────────┘
               │
┌──────────────┴──────────────┐
│  Milvus Vector Database     │
│  (Embedded, File-based)     │
└─────────────────────────────┘
```

## Requirements

- **Python**: 3.13 or higher
- **UV**: Package manager (install from https://docs.astral.sh/uv/)
- **Anthropic API Key**: Required for Claude LLM access
- **System**: macOS, Linux, or Windows with Python 3.13+

## ⚠️ Disclaimer

This project is a **demonstration/proof-of-concept RAG system** designed for educational purposes. The web scraper is configured to work **exclusively with [books.toscrape.com](https://books.toscrape.com)**, a website specifically designed for practicing web scraping techniques.

## Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd simple_ai_chatbot
```

### 2. Create Virtual Environment & Install Dependencies

UV will automatically create and manage the virtual environment:

```bash
uv sync
```

### 3. Configure Environment Variables

Create a `.env` file in the project root:

```bash
# Create from template if one exists
cp .env.example .env

# Or create manually and add:
echo "ANTHROPIC_API_KEY=your_api_key_here" > .env
```

**Required:**
```env
ANTHROPIC_API_KEY=your_api_key_here
```

**Optional** (defaults shown):
```env
# API Configuration
API_BASE_URL=http://localhost:8000

# Web Scraper Settings
SCRAPER_REQUEST_TIMEOUT=10.0
SCRAPER_MAX_RETRIES=3
SCRAPER_RETRY_MIN_WAIT=1.0
SCRAPER_RETRY_MAX_WAIT=5.0
SCRAPER_POLITENESS_DELAY=1.0
SCRAPER_USER_AGENT=simple-ai-chatbot-scraper/0.1
SCRAPER_DEFAULT_DEPTH=2
SCRAPER_DEFAULT_MAX_PAGES=20

# Vector Database
MILVUS_DB_PATH=./data/milvus.db
```

## Usage

### Option 1: Quick Start (CLI Only)

If the API server is already running elsewhere:

```bash
uv run cli.py
```

Then type queries:

```
Query> What is in the knowledge base?
Query> Tell me more about that
Query> exit
```

### Option 2: Full System (API Server + CLI)

**Terminal 1 - Start the API Server:**

```bash
uv run uvicorn main:app --reload
```

The API will be available at `http://localhost:8000`
- Health check: `http://localhost:8000/health`
- API docs: `http://localhost:8000/docs`

**Terminal 2 - Start the CLI:**

```bash
uv run cli.py
```

### API Endpoints

#### Scrape and Index Content

**Note**: This endpoint is pre-configured to scrape only [books.toscrape.com](https://books.toscrape.com) by default.

```bash
curl -X POST http://localhost:8000/api/v1/scrape \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://books.toscrape.com/catalogue/category/books/travel_2/index.html",
    "depth": 2,
    "max_pages": 5,
    "link_pattern": "^/catalogue/(?!category)"
  }'
```

**Parameters**:
- `url`: Starting URL (default: books.toscrape.com travel category)
- `depth`: How deep to crawl (0-10, default: 2)
- `max_pages`: Maximum pages to scrape (1-500, default: 5)
- `link_pattern`: Regex pattern for link filtering (optional)

#### Retrieve Relevant Content

```bash
curl -X POST http://localhost:8000/api/v1/retrieve \
  -H "Content-Type: application/json" \
  -d '{
    "query": "your search query",
    "top_k": 5
  }'
```

## How It Works

### 1. **Web Scraping**
   - Crawl website starting from a URL
   - Extract text content using BeautifulSoup
   - Respect robots.txt and politeness delays

### 2. **Content Chunking**
   - Break pages into semantic chunks (200-500 characters)
   - Preserve metadata (URL, title, price if available)
   - Maintain chunk context for accurate embeddings

### 3. **Embedding & Indexing**
   - Generate 384-dimensional embeddings using `paraphrase-MiniLM-L6-v2`
   - Store embeddings in Milvus vector database
   - Use cosine similarity for fast retrieval

### 4. **Multi-turn Conversations**
   - **Turn 1**: Direct search with user query
   - **Turn 2+**: Rewrite vague questions using conversation history before searching
   - Generate answers grounded in retrieved chunks

### 5. **Answer Generation**
   - Use Claude Haiku for cost-efficient responses
   - Include conversation history for context
   - Ground all answers in retrieved content
