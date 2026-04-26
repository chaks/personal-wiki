"""Tests for async chat engine methods."""
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch
from src.chat import ChatEngine
from src.services.llm_provider import LLMProvider


class MockAsyncIndexer:
    """Test double for async indexer."""

    def __init__(self, wiki_dir):
        self.wiki_dir = wiki_dir
        self.search_calls = []

    def search(self, query: str, top_k: int = 5) -> list[dict]:
        return []

    async def search_async(self, query: str, top_k: int = 5) -> list[dict]:
        self.search_calls.append((query, top_k))
        return [
            {
                "path": "chat-test.md",
                "content": "Chat engine test content",
                "score": 0.95
            }
        ]


class MockAsyncLLMProvider(LLMProvider):
    """Test double for async LLM provider."""

    def __init__(self):
        self.generate_calls = []
        self.generate_stream_calls = []

    def generate(self, prompt: str, system: str | None = None) -> str:
        return "sync response"

    def generate_stream(self, prompt: str, system: str | None = None):
        yield "sync chunk"

    def health_check(self) -> bool:
        return True

    async def generate_async(self, prompt: str, system: str | None = None) -> str:
        self.generate_calls.append((prompt, system))
        return "async LLM response"

    async def generate_stream_async(self, prompt: str, system: str | None = None):
        self.generate_stream_calls.append((prompt, system))
        yield "async chunk 1"
        yield "async chunk 2"

    def embed(self, text: str) -> list[float]:
        return [0.1] * 768

    async def embed_async(self, text: str) -> list[float]:
        return [0.1] * 768


@pytest.fixture
def anyio_backend():
    """Configure anyio backend for async tests."""
    return "asyncio"


@pytest.fixture
def wiki_dir(tmp_path):
    """Create temporary wiki directory."""
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()
    return wiki_dir


class TestAsyncChatEngine:
    """Tests for async ChatEngine methods."""

    @pytest.mark.asyncio
    async def test_search_async(self, wiki_dir):
        """ChatEngine search_async returns search results."""
        mock_indexer = MockAsyncIndexer(wiki_dir)
        mock_llm = MockAsyncLLMProvider()

        engine = ChatEngine(wiki_dir, mock_indexer, llm_provider=mock_llm)
        results = await engine.search_async("test query", top_k=5)

        assert len(results) == 1
        assert results[0]["path"] == "chat-test.md"
        assert results[0]["score"] == 0.95
        assert len(mock_indexer.search_calls) == 1
        assert mock_indexer.search_calls[0] == ("test query", 5)

    @pytest.mark.asyncio
    async def test_query_async_returns_answer_and_context(self, wiki_dir):
        """ChatEngine query_async returns (answer, context) tuple."""
        mock_indexer = MockAsyncIndexer(wiki_dir)
        mock_llm = MockAsyncLLMProvider()

        engine = ChatEngine(wiki_dir, mock_indexer, llm_provider=mock_llm)
        answer, context = await engine.query_async("What is the meaning of life?", top_k=3)

        assert answer == "async LLM response"
        assert len(context) == 1
        assert context[0]["path"] == "chat-test.md"
        assert len(mock_indexer.search_calls) == 1
        assert len(mock_llm.generate_calls) == 1

    @pytest.mark.asyncio
    async def test_query_async_search_error_fallback(self, wiki_dir):
        """ChatEngine query_async handles search errors gracefully."""
        mock_indexer = MockAsyncIndexer(wiki_dir)
        mock_indexer.search_async = AsyncMock(side_effect=Exception("Search error"))
        mock_llm = MockAsyncLLMProvider()

        engine = ChatEngine(wiki_dir, mock_indexer, llm_provider=mock_llm)

        # Should handle the search error and still generate an answer
        answer, context = await engine.query_async("test query", top_k=3)

        # Should still produce an answer even without context
        assert answer == "async LLM response"
        assert context == []

    @pytest.mark.asyncio
    async def test_query_async_llm_error(self, wiki_dir):
        """ChatEngine query_async handles LLM errors."""
        mock_indexer = MockAsyncIndexer(wiki_dir)
        mock_llm = MockAsyncLLMProvider()
        mock_llm.generate_async = AsyncMock(side_effect=Exception("LLM error"))

        engine = ChatEngine(wiki_dir, mock_indexer, llm_provider=mock_llm)

        with pytest.raises(Exception, match="LLM error"):
            await engine.query_async("test query")

    @pytest.mark.asyncio
    async def test_query_async_constructs_prompt_correctly(self, wiki_dir):
        """ChatEngine query_async constructs the prompt with context."""
        mock_indexer = MockAsyncIndexer(wiki_dir)
        mock_llm = MockAsyncLLMProvider()

        engine = ChatEngine(wiki_dir, mock_indexer, llm_provider=mock_llm)
        await engine.query_async("test question", top_k=3)

        assert len(mock_llm.generate_calls) == 1
        prompt, sys_prompt = mock_llm.generate_calls[0]
        assert "test question" in prompt
        assert "Chat engine test content" in prompt
        assert "helpful assistant" in sys_prompt

    @pytest.mark.asyncio
    async def test_search_async_keyword_fallback(self, wiki_dir):
        """ChatEngine search_async falls back to keyword search on error."""
        # Create a wiki file for keyword search to find
        test_file = wiki_dir / "fallback.md"
        test_file.write_text("This contains the keyword testquery123")

        mock_indexer = MockAsyncIndexer(wiki_dir)
        mock_indexer.search_async = AsyncMock(side_effect=Exception("Vector search failed"))
        mock_llm = MockAsyncLLMProvider()

        engine = ChatEngine(wiki_dir, mock_indexer, llm_provider=mock_llm)
        results = await engine.search_async("testquery123", top_k=5)

        # Should fallback to keyword search
        assert len(results) >= 1
        assert any("fallback.md" in r["path"] for r in results)
