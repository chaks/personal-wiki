"""RAG prompt construction for chat queries."""
import html


SYSTEM_PROMPT = (
    "You are a helpful assistant answering questions based on a personal knowledge wiki."
)


def build_rag_prompt(
    context_pages: list[dict],
    question: str,
) -> tuple[str, str]:
    """Build a (system, user) prompt pair for RAG-based chat.

    Args:
        context_pages: List of dicts with 'path' and 'content' keys.
        question: The user's question.

    Returns:
        Tuple of (system_prompt, user_prompt).
    """
    context_text = "\n\n".join(
        f"=== {p['path']} ===\n{p['content']}" for p in context_pages
    )

    system = SYSTEM_PROMPT
    user = (
        f"{SYSTEM_PROMPT}\n\n"
        f"Context from wiki:\n{context_text}\n\n"
        f"Question: {html.escape(question.strip())}\n\n"
        f"Answer based on the context above. If the context doesn't contain "
        f"relevant information, say so."
    )

    return system, user
