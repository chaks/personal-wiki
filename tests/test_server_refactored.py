"""Tests for refactored server with DI."""
import pytest
from unittest.mock import Mock, patch
from pathlib import Path
import tempfile
from fastapi.testclient import TestClient
from src.server import create_app
from src.services.llm_provider import LLMProvider
from src.services.vector_store import VectorStore, SearchPoint


class MockLLMProvider(LLMProvider):
    def __init__(self, response: str = ""):
        self.response = response

    def generate(self, prompt: str, system: str | None = None) -> str:
        return self.response

    def generate_stream(self, prompt: str, system: str | None = None):
        yield self.response

    def health_check(self) -> bool:
        return True

    async def generate_async(self, prompt: str, system: str | None = None) -> str:
        return self.response

    async def generate_stream_async(self, prompt: str, system: str | None = None):
        yield self.response


class MockVectorStore(VectorStore):
    def upsert(self, collection_name: str, points: list[dict]) -> bool:
        return True

    def search(
        self,
        collection_name: str,
        query_vector: list[float],
        limit: int = 5
    ) -> list[SearchPoint]:
        return []

    async def search_async(
        self,
        collection_name: str,
        query_vector: list[float],
        limit: int = 5
    ) -> list[SearchPoint]:
        return []

    async def upsert_async(self, collection_name: str, points: list[dict]) -> bool:
        return True

    def health_check(self) -> bool:
        return True

    def get_collection_info(self) -> dict:
        return {"collections": []}


def test_create_app_accepts_services():
    """create_app accepts injected services."""
    with tempfile.TemporaryDirectory() as tmpdir:
        wiki_dir = Path(tmpdir) / "wiki"
        state_dir = Path(tmpdir) / "state"
        static_dir = Path(tmpdir) / "static"
        wiki_dir.mkdir()
        state_dir.mkdir()
        static_dir.mkdir()

        mock_llm = MockLLMProvider()
        mock_vector = MockVectorStore()

        # Should not raise
        app = create_app(
            wiki_dir=wiki_dir,
            state_dir=state_dir,
            static_dir=static_dir,
            llm_provider=mock_llm,
            vector_store=mock_vector,
        )

        assert app is not None


def test_chat_endpoint_uses_injected_llm():
    """Chat endpoint uses injected LLM provider."""
    with tempfile.TemporaryDirectory() as tmpdir:
        wiki_dir = Path(tmpdir) / "wiki"
        state_dir = Path(tmpdir) / "state"
        static_dir = Path(tmpdir) / "static"
        wiki_dir.mkdir()
        state_dir.mkdir()
        static_dir.mkdir()

        # Create index.html
        (static_dir / "index.html").write_text("<html></html>")

        mock_llm = MockLLMProvider(response="Test answer")
        mock_vector = MockVectorStore()

        app = create_app(
            wiki_dir=wiki_dir,
            state_dir=state_dir,
            static_dir=static_dir,
            llm_provider=mock_llm,
            vector_store=mock_vector,
        )
        client = TestClient(app)

        response = client.post("/chat", json={"message": "Hello"})

        assert response.status_code == 200
