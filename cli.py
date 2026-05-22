"""Interactive RAG chatbot CLI for inspecting retrieved chunks."""

import httpx

from config.config import settings


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


def truncate_url(url: str, max_len: int = 50) -> str:
    """Truncate URL for display."""
    if len(url) <= max_len:
        return url
    return url[: max_len - 3] + "..."


def truncate_text(text: str, max_len: int = 80) -> str:
    """Truncate text excerpt for display."""
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


def display_chunks(chunks: list[dict]) -> None:
    """Display retrieved chunks in a readable format."""
    if not chunks:
        print("  No chunks found.\n")
        return

    for i, chunk in enumerate(chunks, 1):
        score = chunk["score"]
        title = chunk["page_title"]
        url = truncate_url(chunk["source_url"])
        text = truncate_text(chunk["text"])
        price = chunk["price_gbp"]

        price_str = f"£{price:.2f}" if price is not None else "(no price)"

        print(f"  #{i}  [score: {score:.2f}]  {title}")
        print(f"      {price_str}  |  {url}")
        print(f'      "{text}"')
        print()

    print(f"  {len(chunks)} chunk{'s' if len(chunks) != 1 else ''} retrieved.\n")


def main() -> None:
    """Run the interactive REPL."""
    print("RAG Chatbot (chunk viewer mode)")
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

            chunks = retrieve(query)
            display_chunks(chunks)

    except KeyboardInterrupt:
        print("\n")


if __name__ == "__main__":
    main()
