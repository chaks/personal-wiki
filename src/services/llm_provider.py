"""LLM provider abstraction for external service decoupling."""
import asyncio
import logging
from abc import ABC, abstractmethod
from typing import AsyncIterator, Iterator, Optional

logger = logging.getLogger(__name__)


class LLMProvider(ABC):
    """Abstract interface for LLM providers."""

    @abstractmethod
    def generate(self, prompt: str) -> str:
        """Generate a completion for the given prompt.

        Args:
            prompt: The input prompt

        Returns:
            Generated text response
        """
        pass

    @abstractmethod
    def generate_stream(self, prompt: str, system: Optional[str] = None) -> Iterator[str]:
        """Stream a completion for the given prompt.

        Args:
            prompt: The input prompt
            system: Optional system message for chat-based streaming

        Yields:
            Text chunks as they are generated
        """
        pass

    @abstractmethod
    def health_check(self) -> bool:
        """Check if the LLM provider is healthy.

        Returns:
            True if the provider is healthy, False otherwise
        """
        pass

    @abstractmethod
    async def generate_async(self, prompt: str, system: Optional[str] = None) -> str:
        """Asynchronously generate a completion for the given prompt.

        Args:
            prompt: The input prompt
            system: Optional system message for chat-based generation

        Returns:
            Generated text response
        """
        pass

    @abstractmethod
    async def generate_stream_async(self, prompt: str, system: Optional[str] = None) -> AsyncIterator[str]:
        """Asynchronously stream a completion for the given prompt.

        Args:
            prompt: The input prompt
            system: Optional system message for chat-based streaming

        Yields:
            Text chunks as they are generated
        """
        pass

    @abstractmethod
    def embed(self, text: str) -> list[float]:
        """Generate an embedding vector for the given text.

        Args:
            text: The text to embed

        Returns:
            Embedding vector
        """
        pass

    @abstractmethod
    async def embed_async(self, text: str) -> list[float]:
        """Asynchronously generate an embedding vector for the given text.

        Args:
            text: The text to embed

        Returns:
            Embedding vector
        """
        pass


class OllamaProvider(LLMProvider):
    """Ollama implementation of LLM provider."""

    def __init__(self, model: str = "gemma4:e2b"):
        """Initialize Ollama provider.

        Args:
            model: Ollama model name (default: gemma4:e2b)
        """
        self.model = model
        logger.debug(f"OllamaProvider initialized with model: {model}")

    def generate(self, prompt: str, system: Optional[str] = None) -> str:
        """Generate completion using ollama.chat."""
        import ollama

        logger.debug(f"Generating with model={self.model}, prompt_len={len(prompt)}")
        if system:
            messages = [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ]
        else:
            messages = [{"role": "user", "content": prompt}]
        response = ollama.chat(
            model=self.model,
            messages=messages,
        )
        content = response.get("message", {}).get("content", "")
        return content or ""

    def generate_stream(self, prompt: str, system: Optional[str] = None) -> Iterator[str]:
        """Stream completion using ollama.chat."""
        import ollama

        logger.debug(f"Streaming with model={self.model}, prompt_len={len(prompt)}")
        if system:
            messages = [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ]
        else:
            messages = [{"role": "user", "content": prompt}]
        stream = ollama.chat(
            model=self.model,
            messages=messages,
            stream=True,
        )
        for chunk in stream:
            response = chunk.get("message", {}).get("content", "")
            if response:
                yield response

    def health_check(self) -> bool:
        """Check if Ollama service is available."""
        import ollama

        try:
            ollama.list()
            return True
        except Exception as e:
            logger.error(f"Ollama health check failed: {e}")
            return False

    async def generate_async(self, prompt: str, system: Optional[str] = None) -> str:
        """Generate completion asynchronously using ollama.chat."""
        import ollama

        logger.debug(f"Async generating with model={self.model}, prompt_len={len(prompt)}")
        if system:
            messages = [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ]
        else:
            messages = [{"role": "user", "content": prompt}]
        response = await asyncio.to_thread(
            ollama.chat,
            model=self.model,
            messages=messages,
        )
        content = response.get("message", {}).get("content", "")
        return content or ""

    async def generate_stream_async(self, prompt: str, system: Optional[str] = None) -> AsyncIterator[str]:
        """Stream completion asynchronously using ollama.chat."""
        import ollama

        logger.debug(f"Async streaming with model={self.model}, prompt_len={len(prompt)}")
        if system:
            messages = [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ]
        else:
            messages = [{"role": "user", "content": prompt}]
        loop = asyncio.get_event_loop()
        stream = await loop.run_in_executor(
            None,
            lambda: ollama.chat(
                model=self.model,
                messages=messages,
                stream=True,
            ),
        )
        for chunk in stream:
            response = chunk.get("message", {}).get("content", "")
            if response:
                yield response

    def embed(self, text: str) -> list[float]:
        """Generate embedding using ollama.embeddings."""
        import ollama

        logger.debug(f"Embedding with model=nomic-embed-text, text_len={len(text)}")
        response = ollama.embeddings(
            model="nomic-embed-text",
            prompt=text,
        )
        return response["embedding"]

    async def embed_async(self, text: str) -> list[float]:
        """Generate embedding asynchronously using ollama.embeddings."""
        import ollama

        logger.debug(f"Async embedding with model=nomic-embed-text, text_len={len(text)}")
        response = await asyncio.to_thread(
            ollama.embeddings, model="nomic-embed-text", prompt=text
        )
        return response["embedding"]
