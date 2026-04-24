"""Tests for LLM provider abstraction."""
import pytest
from unittest.mock import Mock, patch
from src.services.llm_provider import OllamaProvider


def test_ollama_provider_generate():
    """OllamaProvider generates text via ollama.chat."""
    with patch("ollama.chat") as mock_chat:
        mock_chat.return_value = {"message": {"content": "test response"}}

        provider = OllamaProvider(model="gemma4:e2b")
        result = provider.generate("test prompt")

        assert result == "test response"
        mock_chat.assert_called_once_with(
            model="gemma4:e2b",
            messages=[{"role": "user", "content": "test prompt"}]
        )


def test_ollama_provider_generate_stream():
    """OllamaProvider streams via ollama.generate."""
    with patch("ollama.generate") as mock_generate:
        mock_generate.return_value = iter([
            {"response": "chunk1"},
            {"response": "chunk2"},
        ])

        provider = OllamaProvider(model="gemma4:e2b")
        chunks = list(provider.generate_stream("test prompt"))

        assert chunks == ["chunk1", "chunk2"]


def test_ollama_provider_handles_empty_response():
    """OllamaProvider returns empty string for None content."""
    with patch("ollama.chat") as mock_chat:
        mock_chat.return_value = {"message": {"content": None}}

        provider = OllamaProvider(model="gemma4:e2b")
        result = provider.generate("test prompt")

        assert result == ""


def test_ollama_provider_health_check_healthy():
    """OllamaProvider health check succeeds when service is available."""
    with patch("ollama.list") as mock_list:
        mock_list.return_value = {"models": [{"name": "gemma4:e2b"}]}

        provider = OllamaProvider(model="gemma4:e2b")
        result = provider.health_check()

        assert result is True
        mock_list.assert_called_once()


def test_ollama_provider_health_check_unhealthy():
    """OllamaProvider health check fails when service is unavailable."""
    with patch("ollama.list") as mock_list:
        mock_list.side_effect = Exception("Connection refused")

        provider = OllamaProvider(model="gemma4:e2b")
        result = provider.health_check()

        assert result is False
