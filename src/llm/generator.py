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

    def rewrite_query(self, query: str, history: list[dict]) -> str:
        """Rewrite a follow-up query into a standalone query using conversation history.

        Args:
            query: The user's raw follow-up query
            history: List of prior {role, content} turns (plain Q&A, no chunk context)

        Returns:
            A standalone query suitable for retrieval, or the original query if
            rewriting fails or the model returns an empty string.
        """
        history_text = "\n".join(
            f"{turn['role'].capitalize()}: {turn['content']}" for turn in history
        )
        prompt = (
            "Given the following conversation history, rewrite the user's latest question "
            "as a fully self-contained search query. The rewritten query must include all "
            "necessary context from the history so it can be understood without reading "
            "the conversation. Output only the rewritten query — no explanation, no "
            "punctuation other than what belongs in the query itself.\n\n"
            f"Conversation history:\n{history_text}\n\n"
            f"Latest question: {query}\n\n"
            "Rewritten standalone query:"
        )
        response = self.client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=128,
            messages=[{"role": "user", "content": prompt}],
        )
        rewritten = response.content[0].text.strip()
        return rewritten if rewritten else query

    def generate(
        self, query: str, chunks: list[dict], history: list[dict] | None = None
    ) -> str:
        """Generate an LLM answer based on retrieved chunks and conversation history.

        Args:
            query: User's original question (not the rewritten retrieval query)
            chunks: List of retrieved chunk dictionaries with text, page_title, etc.
            history: Optional list of prior {role, content} turns. When provided,
                     these are prepended to the messages list before the current turn.

        Returns:
            The full answer text as a string.
        """
        if history is None:
            history = []

        context = "\n\n".join(
            f"[{i}] {c['page_title']}\n{c['text']}" for i, c in enumerate(chunks, 1)
        )

        current_user_message = {
            "role": "user",
            "content": f"Context:\n{context}\n\nQuestion: {query}",
        }

        messages = list(history) + [current_user_message]

        print("Answer")
        print("─" * 62)

        parts: list[str] = []
        with self.client.messages.stream(
            model="claude-haiku-4-5-20251001",
            max_tokens=512,
            system=(
                "You are a helpful assistant. Answer the user's question using only "
                "the provided context. If the context does not contain enough information, "
                "say so. When the user refers to something mentioned earlier in the "
                "conversation, use the conversation history to resolve the reference."
            ),
            messages=messages,
        ) as stream:
            for text in stream.text_stream:
                print(text, end="", flush=True)
                parts.append(text)

        print("\n")
        return "".join(parts)
