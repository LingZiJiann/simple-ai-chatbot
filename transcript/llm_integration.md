# Transcript: LLM Integration for RAG Chatbot (Phase 2)

---

## 1. Requirements

**User:**
> I'm ready to implement the LLM for RAG, i want to use claude haiku for this system

**Context:**
Phase 1 (CLI with chunk viewer) was complete. The next step was to integrate an LLM that generates answers based on retrieved chunks. The user wanted to use Claude Haiku model for this purpose.

---

## 2. Design Overview

The LLM integration follows the RAG pattern:

```
User Query
    ↓
[Retrieve top-K chunks via /api/v1/retrieve]
    ↓
[Display chunks with scores and metadata]
    ↓
[Generate answer using Claude Haiku with chunks as context]
    ↓
Stream answer to terminal (word-by-word)
```

Key design principle: Only call the LLM if chunks are found, avoiding wasted API calls on empty results.

---

## 3. Design Decisions

### LLM Model Selection

**Decision:** Use `claude-haiku-4-5-20251001` (Claude Haiku)

**Justification:**
- **Cost-effective**: Haiku is the most affordable Claude model
- **Fast inference**: Lower latency suitable for interactive chatbot
- **Capable enough**: Can handle RAG context understanding and answer generation
- **Available**: Fully available via Anthropic API

Trade-off: Less capable than Opus/Sonnet, but perfect for this use case where context is provided and task is straightforward.

### Architecture: Function vs. Class

**Initial Approach:** Implement `generate_answer()` as a function directly in `cli.py`

**Problem Encountered:**
User wanted separation of concerns: "the llm.py should be in its own folder in src"

**Revised Decision:** Create `src/llm/` folder with `AnswerGenerator` class

**Justification:**
- **Separation of concerns**: LLM logic isolated from CLI orchestration
- **Reusability**: Other components (API endpoints, batch jobs) can use `AnswerGenerator`
- **Extensibility**: Easy to add features (custom system prompts, different models, streaming options)
- **Testability**: Class can be tested independently
- **Clarity**: CLI focuses on interface; LLM generator focuses on answer generation

### Class Design

**Decision:** `AnswerGenerator` takes client in constructor, has `generate()` method

```python
class AnswerGenerator:
    def __init__(self, client: anthropic.Anthropic):
        self.client = client
    
    def generate(self, query: str, chunks: list[dict]) -> None:
        # ... implementation
```

**Justification:**
- Client initialized once at startup (efficient)
- `generate()` method is clean and simple
- Can be extended with additional methods later (e.g., `generate_with_custom_prompt()`)
- Aligns with common Python design patterns

### Context Building Strategy

**Decision:** Build context from chunk title + text for each chunk

```
[1] Title: Budget Travel Guide to Europe
    Budget Travel Guide to Europe: This comprehensive guide covers...

[2] Title: Backpacking Through Asia
    Backpacking Through Asia: A budget traveler's handbook...
```

**Justification:**
- Simple and readable
- Includes both title (for context) and text (for content)
- Numbered for easy reference in model reasoning
- Enough information without being verbose
- Model can reason about sources

### System Prompt Design

**Decision:** Use clear, constraining system prompt

> "You are a helpful assistant. Answer the user's question using only the provided context. If the context does not contain enough information, say so."

**Justification:**
- Clear instructions (use context only, not external knowledge)
- Prevents hallucinations by grounding model to provided chunks
- Tells model what to do when context is insufficient
- Short and unambiguous

### Response Streaming

**Decision:** Stream responses word-by-word to terminal

```python
with client.messages.stream(...) as stream:
    for text in stream.text_stream:
        print(text, end="", flush=True)
```

**Justification:**
- Better user experience (feels responsive)
- Natural chatbot behavior
- Engaging for long responses
- Reduces apparent latency

### API Key Management

**Decision:** Add `anthropic_api_key: str` to config, loaded from `.env`

**Justification:**
- Consistent with existing config pattern (matches `api_base_url`)
- Required field (no default) ensures clear error if missing
- Loaded from `.env` or environment variable via pydantic-settings
- Secure (not hardcoded)

### Conditional LLM Calls

**Decision:** Only call LLM if chunks are found

```python
if chunks:
    generator.generate(query, chunks)
```

**Justification:**
- Avoids unnecessary API calls (cost savings)
- Prevents LLM from trying to answer with no context
- Cleaner UX (no answer shown when no chunks found)
- Efficient (saves both money and latency)

---

## 4. Implementation Timeline

### Step 1: Dependency Management
```bash
uv add anthropic
```
Added anthropic SDK v0.104.0 to project dependencies.

### Step 2: Configuration
Added `anthropic_api_key: str` to `config/config.py` Settings class. No default — will raise error at startup if missing, ensuring user must set it.

### Step 3: LLM Generator Module Creation

Created folder structure:
```
src/llm/
├── __init__.py
└── generator.py
```

Implemented `AnswerGenerator` class in `generator.py` with:
- `__init__(client)` — Store client
- `generate(query, chunks)` — Build context, call Claude Haiku, stream response

### Step 4: CLI Integration

Updated `cli.py`:
- Import `AnswerGenerator` from `src.llm.generator`
- Create instance in `main()` after initializing Anthropic client
- Call `generator.generate(query, chunks)` after `display_chunks()`
- Update startup message from "chunk viewer mode" to "RAG Chatbot"

### Step 5: Documentation
Updated `docs/cli.md` with:
- Architecture diagram showing LLM step
- Example session with streamed answers
- Configuration instructions for API key
- Code reference showing `AnswerGenerator` class
- Troubleshooting section for common LLM issues

---

## 5. Code Structure Details

### AnswerGenerator.generate()

```python
def generate(self, query: str, chunks: list[dict]) -> None:
    # 1. Build context from chunks (title + text)
    context = "\n\n".join(
        f"[{i}] {c['page_title']}\n{c['text']}"
        for i, c in enumerate(chunks, 1)
    )
    
    # 2. Print "Answer" header
    print("Answer")
    print("─" * 62)
    
    # 3. Call Claude Haiku with streaming
    with self.client.messages.stream(
        model="claude-haiku-4-5-20251001",
        max_tokens=512,
        system="You are a helpful assistant. Answer the user's question using only the provided context. If the context does not contain enough information, say so.",
        messages=[
            {
                "role": "user",
                "content": f"Context:\n{context}\n\nQuestion: {query}",
            }
        ],
    ) as stream:
        # 4. Stream response word-by-word
        for text in stream.text_stream:
            print(text, end="", flush=True)
    
    # 5. Print newline after response
    print("\n")
```

**Key Parameters:**
- `max_tokens=512` — Reasonable limit for RAG answers (not too long)
- `stream=True` — Enables word-by-word streaming
- `messages` format — Standard Claude API format

### CLI Integration

```python
def main() -> None:
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    generator = AnswerGenerator(client)
    
    # ... startup messages ...
    
    while True:
        # ... get query, retrieve chunks, display ...
        
        if chunks:
            generator.generate(query, chunks)
```

---

## 6. Error Handling

### Missing API Key
If `ANTHROPIC_API_KEY` is not set:
```
pydantic_core._pydantic_core.ValidationError: 1 validation error for Settings
anthropic_api_key
  Field required [type=missing, input_value={...}, input_type=dict, ...]
```
Clear error message at startup directs user to add key to `.env`.

### API Errors During Generation
If Anthropic API fails during generation:
- Error is raised but caught by outer try/except in `main()`
- User is shown error message
- Loop continues, ready for next query

### Ctrl+C During Streaming
If user presses Ctrl+C during LLM response:
- Stream interrupts gracefully
- Catches `KeyboardInterrupt` in main loop
- Prints newline and exits cleanly

---

## 7. Testing & Verification

### Manual Testing

```bash
# 1. Set up environment
echo "ANTHROPIC_API_KEY=sk-ant-YOUR_KEY" >> .env
uv sync

# 2. Start API server in terminal 1
uvicorn main:app --reload

# 3. Run CLI in terminal 2
uv run cli.py

# 4. Test queries
Query> what are some travel guides?
[Chunks displayed]
[Answer streamed by Claude Haiku]

Query> tell me more about the first one
[Chunks displayed]
[Answer streamed]

Query> [empty query]
[Ignored, re-prompts]

Query> exit
```

### Verification Points

✅ **API Key Loading**: Missing key raises clear error at startup  
✅ **Chunk Retrieval**: Top 5 chunks displayed with scores  
✅ **LLM Integration**: Claude Haiku generates grounded answers  
✅ **Streaming**: Responses appear word-by-word, not all at once  
✅ **Conditional Calls**: No LLM call when chunks are empty  
✅ **Error Handling**: API errors don't crash the loop  
✅ **Clean Exit**: Ctrl+C exits without traceback  

---

## 8. Implementation Challenges & Solutions

### Challenge 1: Separation of Concerns
**Problem**: LLM logic in cli.py made the file harder to maintain and reuse.

**Solution**: Created `src/llm/` folder with `AnswerGenerator` class, kept CLI thin.

### Challenge 2: API Key Security
**Problem**: How to manage Anthropic API key safely?

**Solution**: Use pydantic-settings with `.env` file, consistent with existing config pattern.

### Challenge 3: Avoiding Wasted API Calls
**Problem**: Calling LLM when no chunks found wastes money and latency.

**Solution**: Check `if chunks:` before calling `generate()`.

### Challenge 4: User Experience During Streaming
**Problem**: How to make streamed output feel responsive?

**Solution**: Use `print(..., flush=True)` to ensure immediate output, proper newline handling.

---

## 9. Lessons Learned

1. **Class-Based Design Wins**: The `AnswerGenerator` class is cleaner and more reusable than a function approach.

2. **Separation of Concerns Matters**: Keeping CLI, retrieval, and LLM logic separate made changes easier.

3. **Early Error Messages Help**: Missing API key raises clear error at startup, not later during execution.

4. **Streaming Improves UX**: Word-by-word responses feel more responsive than batch responses.

5. **Conditional LLM Calls Save Cost**: Skipping LLM when no chunks found is efficient both monetarily and latency-wise.

6. **User Feedback Drives Better Design**: "Move to src folder" feedback led to cleaner architecture.

---

## 10. File References

**Modified Files:**
- `cli.py` — Updated to use `AnswerGenerator` class
- `config/config.py` — Added `anthropic_api_key` field
- `pyproject.toml` — Added `anthropic>=0.52.0` dependency (via `uv add`)
- `docs/cli.md` — Updated documentation with LLM integration details

**New Files:**
- `src/llm/__init__.py` — Module exports
- `src/llm/generator.py` — `AnswerGenerator` class implementation

**Related Documentation:**
- `docs/cli.md` — Complete CLI documentation with LLM examples
- `docs/retrieval.md` — Underlying retrieval API (unchanged)
- `transcript/cli.md` — Previous CLI implementation transcript

---

## 11. Future Enhancements

### Possible Improvements

1. **Custom System Prompts**: Add method to accept custom system prompts for different use cases
2. **Model Switching**: Support different Claude models (Opus, Sonnet) via configuration
3. **Context Window Optimization**: Smart truncation if context gets very large
4. **Response Caching**: Cache answers for repeated queries
5. **Feedback Integration**: Let users rate answers, improve ranking
6. **Multi-turn Conversation**: Maintain conversation history for follow-up questions
7. **Source Attribution**: Automatically cite which chunks were used in the answer
8. **Custom Formatters**: Different output formats (JSON, Markdown, HTML)

### Architecture Ready For:
- Adding retrieval to API endpoints (endpoint could use same `AnswerGenerator`)
- Batch query processing
- Different embedding models (retrieval module is separate)
- Custom LLM providers (plugin new generators in `src/llm/`)

---

## 12. Summary

Phase 2 successfully integrated Claude Haiku into the RAG chatbot CLI. The implementation:
- **Separates concerns** with clean class-based design
- **Avoids wasted API calls** by checking for chunks first
- **Provides excellent UX** with word-by-word streaming
- **Stays maintainable** through clear architecture
- **Enables future extensions** without major refactoring

The system now provides a complete RAG experience: retrieve relevant chunks, generate grounded answers, stream responses naturally.
