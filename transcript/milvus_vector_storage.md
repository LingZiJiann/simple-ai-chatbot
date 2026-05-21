# Transcript: Milvus Vector Storage Integration for Chunks

---

## 1. Requirements

**User:**
> Read the web scraping documentation and store chunks into a vector database.
>
> Requirements:
> 1. Convert chunks to embeddings using embedding model (~50MB, 384-dim)
> 2. Use Milvus Lite as the vector database (local `.db` file, no server needed)
> 3. Store embeddings with chunk metadata in Milvus

---

## 2. Design Decisions

### Embedding Model Selection

Initially planned to use `pymilvus.model.DefaultEmbeddingFunction()`, but encountered compatibility issues with newer transformers versions.

**Resolution:** Use `sentence-transformers.SentenceTransformer("paraphrase-MiniLM-L6-v2")` instead — provides 384-dim vectors, more stable, works with current package versions.

### Database Path Organization

> "For my db file help create a data folder and store it inside that folder"

**Decision:** Store database at `./data/milvus.db` with automatic folder creation on server startup.

### FastAPI Dependency Injection

> "Explain to me the FastAPI dependency without coupling routers to app"

**Pattern:** Use `get_vector_store(request: Request)` dependency that retrieves `request.app.state.vector_store` — eliminates circular imports and decouples routers from main app module.

### Lifespan Context Manager

> "Explain to me what does adding lifespan to main.py does"

**Purpose:** 
- Defer model download and VectorStore initialization to server startup (not import time)
- Automatic cleanup on shutdown via `store.close()`
- Works correctly with FastAPI's TestClient

---
