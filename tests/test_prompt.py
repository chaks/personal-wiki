"""Tests for RAG prompt builder."""
import pytest
from src.prompt import build_rag_prompt


class TestBuildRagPrompt:
    """Tests for build_rag_prompt."""

    def test_returns_system_and_user_tuple(self):
        """build_rag_prompt returns a tuple of (system, user)."""
        context = [{"path": "page.md", "content": "Some content"}]
        system, user = build_rag_prompt(context, "What is X?")
        assert isinstance(system, str)
        assert isinstance(user, str)

    def test_system_prompt_contains_behavioral_instruction(self):
        """System prompt tells the assistant to answer from wiki context."""
        context = [{"path": "page.md", "content": "Some content"}]
        system, _ = build_rag_prompt(context, "What is X?")
        assert "helpful assistant" in system
        assert "personal knowledge wiki" in system

    def test_user_prompt_contains_context_and_question(self):
        """User prompt contains formatted context and the question."""
        context = [
            {"path": "alpha.md", "content": "Alpha content"},
            {"path": "beta.md", "content": "Beta content"},
        ]
        _, user = build_rag_prompt(context, "What is Y?")
        assert "=== alpha.md ===" in user
        assert "Alpha content" in user
        assert "=== beta.md ===" in user
        assert "Beta content" in user
        assert "What is Y?" in user

    def test_user_prompt_sanitizes_html_injection(self):
        """User prompt HTML-escapes the question to prevent injection."""
        context = [{"path": "page.md", "content": "content"}]
        _, user = build_rag_prompt(context, "<script>alert(1)</script>")
        assert "<script>" not in user
        assert "&lt;script&gt;" in user

    def test_user_prompt_strips_whitespace(self):
        """User prompt strips leading/trailing whitespace from question."""
        context = [{"path": "page.md", "content": "content"}]
        _, user = build_rag_prompt(context, "   Hello?   ")
        assert "Hello?" in user

    def test_empty_context_yields_valid_prompt(self):
        """build_rag_prompt works with zero context pages."""
        system, user = build_rag_prompt([], "What is Z?")
        assert "helpful assistant" in system
        assert "What is Z?" in user
        assert "===" not in user

    def test_context_separator_is_double_newline(self):
        """Multiple context pages are separated by two newlines."""
        context = [
            {"path": "a.md", "content": "A"},
            {"path": "b.md", "content": "B"},
        ]
        _, user = build_rag_prompt(context, "Q?")
        assert "=== a.md ===\nA\n\n=== b.md ===\nB" in user
