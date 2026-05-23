"""Interactive RAG chatbot CLI with LLM-powered question answering."""

import anthropic
import httpx

from config.config import settings
from src.llm.generator import AnswerGenerator


RETRIEVE_ENDPOINT = f"{settings.api_base_url}/api/v1/retrieve"


def retrieve(query: str, top_k: int = 5) -> list[dict]:
    """Retrieve top-k chunks matching the query via the API."""
    try:
        response = httpx.post(
            RETRIEVE_ENDPOINT,
            json={"query": query, "top_k": top_k},
            timeout=10.0,
        )
        response.raise_for_status()
        return response.json()["results"]
    except httpx.HTTPError as e:
        print(f"  Error: {e}")
        return []


def main() -> None:
    """Run the interactive REPL."""
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    generator = AnswerGenerator(client)

    # In-memory conversation history. Each entry: {"role": "user"|"assistant", "content": str}
    # Only plain Q&A is stored — no chunk context. Grows by 2 entries per turn.
    history: list[dict] = []

    print("RAG Chatbot")
    print(f"Connected to {settings.api_base_url}")
    print("Type your query and press Enter. Type 'exit' or Ctrl+C to quit.")
    print("─" * 62)
    print()

    try:
        while True:
            try:
                query = input("Query> ").strip()
            except EOFError:
                # Handle when input stream ends (e.g., piped input)
                break

            if not query:
                # Ignore empty input
                continue

            if query.lower() in ("exit", "quit"):
                break

            # Rewrite the query for retrieval when there is prior history.
            # On the first turn history is empty, so we skip rewriting entirely.
            if history:
                retrieval_query = generator.rewrite_query(query, history)
            else:
                retrieval_query = query

            chunks = retrieve(retrieval_query)

            if chunks:
                # Generate using the ORIGINAL query + full history.
                answer = generator.generate(query, chunks, history)

                # Append original query and answer to history (plain Q&A only).
                history.append({"role": "user", "content": query})
                history.append({"role": "assistant", "content": answer})

    except KeyboardInterrupt:
        print("\n")


if __name__ == "__main__":
    main()
