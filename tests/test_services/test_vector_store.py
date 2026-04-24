"""Tests for vector store abstraction."""
import pytest
from unittest.mock import Mock, patch
from src.services.vector_store import QdrantStore, SearchPoint


@patch("qdrant_client.QdrantClient")
def test_qdrant_store_upsert(MockClient):
    """QdrantStore upserts points via client.upsert."""
    mock_client = Mock()
    mock_result = Mock(status="completed")
    mock_client.upsert.return_value = mock_result
    MockClient.return_value = mock_client

    store = QdrantStore(url="http://localhost:6333")
    result = store.upsert(
        collection_name="test",
        points=[{"id": 1, "vector": [0.1, 0.2], "payload": {"text": "test"}}]
    )

    assert result is True
    mock_client.upsert.assert_called_once()


@patch("qdrant_client.QdrantClient")
def test_qdrant_store_search(MockClient):
    """QdrantStore searches via client.search."""
    mock_client = Mock()
    mock_result = Mock(score=0.95, payload={"text": "result"})
    mock_client.search.return_value = [mock_result]
    MockClient.return_value = mock_client

    store = QdrantStore(url="http://localhost:6333")
    results = store.search(
        collection_name="test",
        query_vector=[0.1, 0.2],
        limit=5
    )

    assert len(results) == 1
    assert results[0].score == 0.95
    assert isinstance(results[0], SearchPoint)
