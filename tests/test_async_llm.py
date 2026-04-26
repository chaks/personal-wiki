"""Tests for async LLM provider methods."""
import pytest
from unittest.mock import AsyncMock, Mock, patch
from src.services.llm_provider import OllamaProvider


@pytest.fixture
def anyio_backend():
    """Configure anyio backend for async tests."""
    return "asyncio"


class TestAsyncLLMProvider:
    """Tests for async LLM provider methods."""

    @pytest.mark.asyncio
    async def test_ollama_provider_generate_async(self):
        """OllamaProvider generates text asynchronously via ollama.chat."""
        with patch("src.services.llm_provider.asyncio.to_thread") as mock_to_thread:
            mock_to_thread.return_value = {"message": {"content": "async test response"}}

            provider = OllamaProvider(model="gemma4:e2b")
            result = await provider.generate_async("test prompt")

            assert result == "async test response"
            mock_to_thread.assert_called_once()

    @pytest.mark.asyncio
    async def test_ollama_provider_generate_stream_async(self):
        """OllamaProvider streams text asynchronously via ollama.chat."""
        def sync_gen():
            yield {"message": {"content": "chunk1"}}
            yield {"message": {"content": "chunk2"}}
            yield {"message": {"content": "chunk3"}}

        with patch("src.services.llm_provider.asyncio.get_event_loop") as mock_loop:
            mock_loop.return_value.run_in_executor = AsyncMock(return_value=sync_gen())

            provider = OllamaProvider(model="gemma4:e2b")
            chunks = []
            async for chunk in provider.generate_stream_async("test prompt"):
                chunks.append(chunk)

            assert chunks == ["chunk1", "chunk2", "chunk3"]

    @pytest.mark.asyncio
    async def test_ollama_provider_generate_async_empty_response(self):
        """OllamaProvider returns empty string for None content in async mode."""
        with patch("src.services.llm_provider.asyncio.to_thread") as mock_to_thread:
            mock_to_thread.return_value = {"message": {"content": None}}

            provider = OllamaProvider(model="gemma4:e2b")
            result = await provider.generate_async("test prompt")

            assert result == ""

    @pytest.mark.asyncio
    async def test_ollama_provider_generate_async_handles_exception(self):
        """OllamaProvider handles exceptions in async generate."""
        with patch("src.services.llm_provider.asyncio.to_thread") as mock_to_thread:
            mock_to_thread.side_effect = Exception("Connection error")

            provider = OllamaProvider(model="gemma4:e2b")
            with pytest.raises(Exception, match="Connection error"):
                await provider.generate_async("test prompt")

    @pytest.mark.asyncio
    async def test_ollama_provider_generate_stream_async_handles_exception(self):
        """OllamaProvider handles exceptions in async stream generate."""
        with patch("src.services.llm_provider.asyncio.get_event_loop") as mock_loop:
            mock_loop.return_value.run_in_executor = AsyncMock(side_effect=Exception("Connection error"))

            provider = OllamaProvider(model="gemma4:e2b")
            with pytest.raises(Exception, match="Connection error"):
                async for _ in provider.generate_stream_async("test prompt"):
                    pass

    @pytest.mark.asyncio
    async def test_ollama_provider_embed_async(self):
        """OllamaProvider embed_async returns embedding via ollama.embeddings."""
        with patch("src.services.llm_provider.asyncio.to_thread") as mock_to_thread:
            mock_to_thread.return_value = {"embedding": [0.1, 0.2, 0.3]}

            provider = OllamaProvider(model="gemma4:e2b")
            result = await provider.embed_async("test text")

            assert result == [0.1, 0.2, 0.3]
            mock_to_thread.assert_called_once()
            args, kwargs = mock_to_thread.call_args
            assert kwargs["model"] == "nomic-embed-text"
            assert kwargs["prompt"] == "test text"
