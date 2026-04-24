"""Tests for refactored WikiIndexer with DI."""
import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import tempfile
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


def test_indexer_uses_vector_store():
    """WikiIndexer uses injected vector store."""
    with tempfile.TemporaryDirectory() as tmpdir:
        wiki_dir = Path(tmpdir)
        mock_store = MockVectorStore()

        indexer = WikiIndexer(wiki_dir=wiki_dir, vector_store=mock_store)

        # Create a test page
        test_page = wiki_dir / "test.md"
        test_page.write_text("# Test\n\nContent")

        with patch("src.indexer.ollama.embeddings") as mock_embeddings:
            mock_embeddings.return_value = {"embedding": [0.1] * 768}
            indexer.index_page(test_page)

        assert len(mock_store.upserted_points) == 1


def test_indexer_backward_compatible():
    """WikiIndexer still works without explicit vector store."""
    with tempfile.TemporaryDirectory() as tmpdir:
        wiki_dir = Path(tmpdir)

        # Should work with just wiki_dir (uses Qdrant default)
        indexer = WikiIndexer(wiki_dir=wiki_dir)

        # vector_store should be None until accessed
        assert indexer.wiki_dir == wiki_dir
        assert indexer.vector_store is None
