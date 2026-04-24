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


@patch("qdrant_client.QdrantClient")
def test_qdrant_store_health_check_healthy(MockClient):
    """QdrantStore health check succeeds when service is available."""
    mock_client = Mock()
    mock_client.get_collections.return_value = Mock(collections=[])
    MockClient.return_value = mock_client

    store = QdrantStore(url="http://localhost:6333")
    result = store.health_check()

    assert result is True


@patch("qdrant_client.QdrantClient")
def test_qdrant_store_health_check_unhealthy(MockClient):
    """QdrantStore health check fails when service is unavailable."""
    mock_client = Mock()
    mock_client.get_collections.side_effect = Exception("Timeout")
    MockClient.return_value = mock_client

    store = QdrantStore(url="http://localhost:6333")
    result = store.health_check()

    assert result is False


@patch("qdrant_client.QdrantClient")
def test_qdrant_store_get_collection_info(MockClient):
    """QdrantStore get_collection_info returns collection details."""
    mock_client = Mock()
    mock_collection = Mock()
    mock_collection.name = "test_collection"
    mock_collection.points_count = 100
    mock_collection.vectors_count = 100
    mock_client.get_collections.return_value = Mock(collections=[mock_collection])
    MockClient.return_value = mock_client

    store = QdrantStore(url="http://localhost:6333")
    info = store.get_collection_info()

    assert "collections" in info
    assert len(info["collections"]) == 1
    assert info["collections"][0]["name"] == "test_collection"
    assert info["collections"][0]["points_count"] == 100
