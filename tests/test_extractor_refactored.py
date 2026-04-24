"""Tests for refactored EntityExtractor with DI."""
import pytest
from src.extractor import EntityExtractor
from src.services.llm_provider import LLMProvider


class MockLLMProvider(LLMProvider):
    """Test double for LLM provider."""

    def __init__(self, response: str = ""):
        self.response = response
        self.call_count = 0

    def generate(self, prompt: str) -> str:
        self.call_count += 1
        return self.response

    def generate_stream(self, prompt: str):
        yield self.response


def test_extractor_uses_llm_provider():
    """EntityExtractor uses injected LLM provider."""
    mock_provider = MockLLMProvider(response="ENTITY: Test | type | description")
    extractor = EntityExtractor(llm_provider=mock_provider)

    entities = extractor.extract("test document")

    assert len(entities) == 1
    assert entities[0].name == "Test"
    assert mock_provider.call_count == 1


def test_extractor_backward_compatible():
    """EntityExtractor still works without explicit provider."""
    extractor = EntityExtractor(model="gemma4:e2b")

    # Should instantiate default OllamaProvider
    assert extractor.llm_provider is not None
