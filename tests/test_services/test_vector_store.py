"""Tests for vector store abstraction (async core)."""
import pytest
from unittest.mock import AsyncMock, Mock, patch
from src.services.vector_store import QdrantStore, SearchPoint, SyncVectorStore


class TestQdrantStoreAsyncCore:
    """Tests for QdrantStore async methods (the canonical interface)."""

    @pytest.mark.asyncio
    async def test_upsert(self):
        """QdrantStore upsert (async) stores points via sync client in thread."""
        with patch("qdrant_client.QdrantClient") as MockClient:
            mock_client = Mock()
            mock_result = Mock(status="completed")
            mock_client.upsert.return_value = mock_result
            MockClient.return_value = mock_client

            store = QdrantStore(url="http://localhost:6333")
            result = await store.upsert(
                collection_name="test",
                points=[{"id": 1, "vector": [0.1, 0.2], "payload": {"text": "test"}}]
            )

            assert result is True
            mock_client.upsert.assert_called_once()

    @pytest.mark.asyncio
    async def test_upsert_failed(self):
        """QdrantStore upsert returns False on failed status."""
        with patch("qdrant_client.QdrantClient") as MockClient:
            mock_client = Mock()
            mock_result = Mock(status="failed")
            mock_client.upsert.return_value = mock_result
            MockClient.return_value = mock_client

            store = QdrantStore(url="http://localhost:6333")
            result = await store.upsert(
                collection_name="test",
                points=[{"id": 1, "vector": [0.1], "payload": {}}]
            )

            assert result is False

    @pytest.mark.asyncio
    async def test_search(self):
        """QdrantStore search (async) queries via sync client in thread."""
        with patch("qdrant_client.QdrantClient") as MockClient:
            mock_client = Mock()
            mock_point = Mock()
            mock_point.id = "test-id"
            mock_point.score = 0.95
            mock_point.payload = {"text": "result"}
            mock_point.vector = None
            mock_client.query_points.return_value = Mock(points=[mock_point])
            MockClient.return_value = mock_client

            store = QdrantStore(url="http://localhost:6333")
            results = await store.search(
                collection_name="test",
                query_vector=[0.1, 0.2],
                limit=5
            )

            assert len(results) == 1
            assert results[0].score == 0.95
            assert isinstance(results[0], SearchPoint)

    @pytest.mark.asyncio
    async def test_upsert_async_removed(self):
        """upsert_async method no longer exists."""
        with patch("qdrant_client.QdrantClient") as MockClient:
            mock_client = Mock()
            MockClient.return_value = mock_client

            store = QdrantStore(url="http://localhost:6333")
            assert not hasattr(store, 'upsert_async') or not callable(getattr(store, 'upsert_async', None))


class TestSyncVectorStoreWrapper:
    """Tests for SyncVectorStore — the thin sync facade."""

    def test_upsert_wraps_async(self):
        """SyncVectorStore.upsert wraps the async inner call."""
        class MockAsyncStore:
            async def upsert(self, collection_name, points):
                return True
            async def search(self, collection_name, query_vector, limit=5):
                return []

        wrapper = SyncVectorStore(MockAsyncStore())
        result = wrapper.upsert("test", [{"id": 1}])
        assert result is True

    def test_search_wraps_async(self):
        """SyncVectorStore.search wraps the async inner call."""
        class MockAsyncStore:
            async def upsert(self, collection_name, points):
                return True
            async def search(self, collection_name, query_vector, limit=5):
                return [SearchPoint(id="x", score=0.9, payload={})]

        wrapper = SyncVectorStore(MockAsyncStore())
        results = wrapper.search("test", [0.1], limit=3)
        assert len(results) == 1
        assert results[0].id == "x"
