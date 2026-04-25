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
    def generate_stream(self, prompt: str) -> Iterator[str]:
        """Stream a completion for the given prompt.

        Args:
            prompt: The input prompt

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
    async def generate_async(self, prompt: str) -> str:
        """Asynchronously generate a completion for the given prompt.

        Args:
            prompt: The input prompt

        Returns:
            Generated text response
        """
        pass

    @abstractmethod
    async def generate_stream_async(self, prompt: str) -> AsyncIterator[str]:
        """Asynchronously stream a completion for the given prompt.

        Args:
            prompt: The input prompt

        Yields:
            Text chunks as they are generated
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

    def generate_stream(self, prompt: str) -> Iterator[str]:
        """Stream completion using ollama.generate."""
        import ollama

        logger.debug(f"Streaming with model={self.model}, prompt_len={len(prompt)}")
        stream = ollama.generate(model=self.model, prompt=prompt, stream=True)
        for chunk in stream:
            response = chunk.get("response", "")
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

    async def generate_async(self, prompt: str) -> str:
        """Generate completion asynchronously using ollama.chat."""
        import ollama

        logger.debug(f"Async generating with model={self.model}, prompt_len={len(prompt)}")
        # ollama doesn't have native async support, so we use asyncio.to_thread
        response = await asyncio.to_thread(
            ollama.chat,
            model=self.model,
            messages=[{"role": "user", "content": prompt}]
        )
        content = response.get("message", {}).get("content", "")
        return content or ""

    async def generate_stream_async(self, prompt: str) -> AsyncIterator[str]:
        """Stream completion asynchronously using ollama.generate."""
        import ollama

        logger.debug(f"Async streaming with model={self.model}, prompt_len={len(prompt)}")
        # ollama doesn't have native async support, so we use asyncio.to_thread
        # We need to run the streaming in a thread and yield results
        loop = asyncio.get_event_loop()
        stream = await loop.run_in_executor(
            None,
            lambda: ollama.generate(model=self.model, prompt=prompt, stream=True)
        )
        for chunk in stream:
            response = chunk.get("response", "")
            if response:
                yield response
