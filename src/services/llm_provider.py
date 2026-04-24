"""LLM provider abstraction for external service decoupling."""
import logging
from abc import ABC, abstractmethod
from typing import Iterator

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


class OllamaProvider(LLMProvider):
    """Ollama implementation of LLM provider."""

    def __init__(self, model: str = "gemma4:e2b"):
        """Initialize Ollama provider.

        Args:
            model: Ollama model name (default: gemma4:e2b)
        """
        self.model = model
        logger.debug(f"OllamaProvider initialized with model: {model}")

    def generate(self, prompt: str) -> str:
        """Generate completion using ollama.chat."""
        import ollama

        logger.debug(f"Generating with model={self.model}, prompt_len={len(prompt)}")
        response = ollama.chat(
            model=self.model,
            messages=[{"role": "user", "content": prompt}]
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
