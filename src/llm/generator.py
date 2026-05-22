"""LLM-powered answer generation for RAG."""

import anthropic


class AnswerGenerator:
    """Generate LLM answers based on retrieved chunks."""

    def __init__(self, client: anthropic.Anthropic):
        """Initialize the generator with an Anthropic client.

        Args:
            client: Initialized Anthropic client
        """
        self.client = client

    def generate(self, query: str, chunks: list[dict]) -> None:
        """Generate an LLM answer based on retrieved chunks.

        Args:
            query: User's original question
            chunks: List of retrieved chunk dictionaries with text, page_title, etc.
        """
        context = "\n\n".join(
            f"[{i}] {c['page_title']}\n{c['text']}" for i, c in enumerate(chunks, 1)
        )
        print("Answer")
        print("─" * 62)
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
            for text in stream.text_stream:
                print(text, end="", flush=True)
        print("\n")
