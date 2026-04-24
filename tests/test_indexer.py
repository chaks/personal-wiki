# tests/test_indexer.py
import pytest
from pathlib import Path
from unittest.mock import Mock, patch
from src.indexer import WikiIndexer
from src.services.vector_store import VectorStore, SearchPoint


class MockVectorStore(VectorStore):
    """Test double for vector store."""

    def __init__(self):
        self.upserted_points = []
        self.search_queries = []

    def upsert(self, collection_name: str, points: list[dict]) -> bool:
        self.upserted_points.extend(points)
        return True

    def search(
        self,
        collection_name: str,
        query_vector: list[float],
        limit: int = 5
    ) -> list[SearchPoint]:
        self.search_queries.append((query_vector, limit))
        return [
            SearchPoint(
                id="test-id",
                score=0.95,
                payload={"path": "test.md", "content": "test content"}
            )
        ]

    async def search_async(
        self,
        collection_name: str,
        query_vector: list[float],
        limit: int = 5
    ) -> list[SearchPoint]:
        self.search_queries.append((query_vector, limit))
        return [
            SearchPoint(
                id="test-id",
                score=0.95,
                payload={"path": "test.md", "content": "test content"}
            )
        ]

    async def upsert_async(self, collection_name: str, points: list[dict]) -> bool:
        self.upserted_points.extend(points)
        return True

    def health_check(self) -> bool:
        return True

    def get_collection_info(self) -> dict:
        return {"collections": []}


@pytest.fixture
def wiki_dir(tmp_path):
    """Create temporary wiki directory."""
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()
    return wiki_dir


def test_indexer_initializes(wiki_dir):
    """Indexer initializes with wiki directory."""
    indexer = WikiIndexer(wiki_dir, "http://localhost:6333")
    assert indexer.wiki_dir == wiki_dir
    assert indexer.qdrant_url == "http://localhost:6333"


@patch("src.indexer.ollama")
def test_index_wiki_page(mock_ollama, wiki_dir):
    """Indexer embeds and stores wiki page."""
    mock_ollama.embeddings.return_value = {"embedding": [0.1] * 768}

    mock_store = MockVectorStore()

    page_file = wiki_dir / "concepts" / "test.md"
    page_file.parent.mkdir()
    page_file.write_text("---\ntitle: Test\n---\n\nContent here")

    indexer = WikiIndexer(wiki_dir, "http://localhost:6333", vector_store=mock_store)
    indexer.index_page(page_file)

    assert len(mock_store.upserted_points) == 1


@patch("src.indexer.ollama")
def test_search_returns_results(mock_ollama, wiki_dir):
    """Search returns relevant wiki pages."""
    mock_ollama.embeddings.return_value = {"embedding": [0.1] * 768}

    mock_store = MockVectorStore()

    indexer = WikiIndexer(wiki_dir, "http://localhost:6333", vector_store=mock_store)
    results = indexer.search("test query", top_k=5)

    assert isinstance(results, list)
    assert len(results) == 1
    assert results[0]["path"] == "test.md"
