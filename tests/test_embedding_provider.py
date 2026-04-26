"""Tests for embedding provider abstraction."""
import pytest
from unittest.mock import AsyncMock, patch
from src.services.embedding_provider import OllamaEmbeddingProvider


class TestOllamaProviderEmbeddingProvider:
    """Tests for OllamaProvider embed methods."""

    def test_embed_returns_embedding(self):
        """OllamaEmbeddingProvider.embed returns embedding via ollama.embeddings."""
        with patch("ollama.embeddings") as mock_embeddings:
            mock_embeddings.return_value = {"embedding": [0.1, 0.2, 0.3]}

            provider = OllamaEmbeddingProvider(model="nomic-embed-text")
            result = provider.embed("test text")

            assert result == [0.1, 0.2, 0.3]
            mock_embeddings.assert_called_once_with(
                model="nomic-embed-text", prompt="test text"
            )

    @pytest.mark.asyncio
    async def test_embed_async_returns_embedding(self):
        """OllamaEmbeddingProvider.embed_async returns embedding via ollama.embeddings."""
        with patch("src.services.embedding_provider.asyncio.to_thread") as mock_to_thread:
            mock_to_thread.return_value = {"embedding": [0.1, 0.2, 0.3]}

            provider = OllamaEmbeddingProvider(model="nomic-embed-text")
            result = await provider.embed_async("test text")

            assert result == [0.1, 0.2, 0.3]
            mock_to_thread.assert_called_once()
            args, kwargs = mock_to_thread.call_args
            assert kwargs["model"] == "nomic-embed-text"
            assert kwargs["prompt"] == "test text"

    def test_dimension_returns_768(self):
        """OllamaEmbeddingProvider.dimension returns 768 for nomic-embed-text."""
        provider = OllamaEmbeddingProvider()
        assert provider.dimension == 768

    def test_default_model_is_nomic_embed_text(self):
        """OllamaEmbeddingProvider defaults to nomic-embed-text."""
        provider = OllamaEmbeddingProvider()
        assert provider.model == "nomic-embed-text"

    def test_custom_model(self):
        """OllamaEmbeddingProvider accepts custom model name."""
        provider = OllamaEmbeddingProvider(model="custom-model")
        assert provider.model == "custom-model"
