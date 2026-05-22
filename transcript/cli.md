# Transcript: RAG Chatbot CLI for Chunk Inspection

---

## 1. Requirements

**User:**
> Read this documentation and understand my retrieval and fastapi endpoint, I want to implement a cli so the user can search relevant chunks instead of using swagger ui

**Context:**
The project has a working FastAPI retrieval endpoint (`POST /api/v1/retrieve`) that performs semantic search over indexed chunks using Milvus and SentenceTransformer embeddings. The user wanted a command-line interface to query this endpoint instead of manually hitting it through Swagger UI.

---

## 2. Initial Context Clarification

**User (additional context):**
> this is actually for a rag, the reason i wanna do this is so i can see the retrieved chunks, the future implementation is for a LLM to answer the user query based on the retrieved chunks. so in future, the cli should handle like a chatbot

**Key Insight:** This is Phase 1 of a RAG (Retrieval-Augmented Generation) chatbot. The immediate need is to visualize retrieved chunks for debugging and verification. The long-term vision is to add an LLM that generates answers based on those chunks. The architecture should be designed with this future extension in mind.

---

## 3. Design Decisions

### Interactive REPL vs. Single-Shot Command

**Consideration:**
> Should the CLI accept a single query as a command-line argument (`python cli.py "query"`), or run an interactive loop?

**Decision:** Interactive REPL (Read-Eval-Print Loop)

**Justification:**
- **Efficiency**: The embedding model loads once at startup (~80-100 MB, slow to load). An interactive loop reuses it across multiple queries. Single-shot would reload the model per query, which is wasteful.
- **UX**: The loop already mirrors chatbot behavior — user types, gets results, types again. This is the mental model users expect from a RAG system.
- **Extensibility**: Adding an LLM response step later fits naturally into the loop structure. The loop already has all the machinery needed.
- **Testing**: Developers can run multiple queries in one session without restarting.

### Direct VectorStore Access vs. HTTP Client

**Initial Approach:** Direct instantiation of `VectorStore(db_path)`, bypassing the API.

**Problem Encountered:**
When running with `uv run cli.py` while the FastAPI server was also running, Milvus connection conflicts occurred:
```
pymilvus.exceptions.ConnectionConfigException: <ConnectionConfigException: (code=1, message=Open local milvus failed)>
```

**Revised Decision:** Use HTTP client to call the existing FastAPI endpoint.

**Justification:**
- **No Lock Conflicts**: The server holds the Milvus connection; the CLI never touches the database directly.
- **Stateless**: The CLI is now a thin HTTP client with no state to manage.
- **Reusability**: The CLI uses the exact same validation and logic as Swagger UI users.
- **Deployment**: CLI can run from different machines (not just where the DB lives).
- **Separation of Concerns**: Retrieval logic stays in the API; the CLI just displays results.

**Trade-off**: Requires the FastAPI server to be running. This is acceptable since the server is typically always running in production.

### Fixed Defaults vs. Command-Line Flags

**Initial Plan:** Support optional flags like `--top-k`, `--min-score`, `--db-path`.

**User Feedback:**
> no need for optional flags

**Decision:** Remove all flags; use hardcoded defaults.

**Justification:**
- **Simplicity**: The CLI is simpler to use and understand with no options to learn.
- **MVP**: Flags can be added later if needed; focus on core functionality now.
- **Common Case**: Most users want the same defaults (top 5 results, default scoring).

**Hardcoded Defaults:**
- `top_k = 5` (reasonable balance between breadth and detail)
- `timeout = 10.0s` (HTTP request timeout)
- `BASE_URL = "http://localhost:8000"` (standard dev environment)
