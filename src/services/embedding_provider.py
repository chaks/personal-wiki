"""Embedding provider abstraction for text vectorization."""
import asyncio
import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class EmbeddingProvider(ABC):
    """Abstract interface for embedding providers."""

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Dimension of embedding vectors produced by this provider."""
        ...

    @abstractmethod
    def embed(self, text: str) -> list[float]:
        """Generate an embedding vector for the given text."""
        pass

    @abstractmethod
    async def embed_async(self, text: str) -> list[float]:
        """Asynchronously generate an embedding vector for the given text."""
        pass


NOMIC_EMBED_TEXT_DIMENSION = 768


class OllamaEmbeddingProvider(EmbeddingProvider):
    """Ollama implementation of embedding provider."""

    def __init__(self, model: str = "nomic-embed-text"):
        self.model = model
        logger.debug(f"OllamaEmbeddingProvider initialized with model: {model}")

    @property
    def dimension(self) -> int:
        return NOMIC_EMBED_TEXT_DIMENSION

    def embed(self, text: str) -> list[float]:
        import ollama

        logger.debug(f"Embedding with model={self.model}, text_len={len(text)}")
        response = ollama.embeddings(model=self.model, prompt=text)
        return response["embedding"]

    async def embed_async(self, text: str) -> list[float]:
        import ollama

        logger.debug(f"Async embedding with model={self.model}, text_len={len(text)}")
        response = await asyncio.to_thread(
            ollama.embeddings, model=self.model, prompt=text
        )
        return response["embedding"]
