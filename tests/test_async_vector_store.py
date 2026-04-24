"""Tests for async vector store methods."""
import pytest
from unittest.mock import AsyncMock, Mock, patch
from src.services.vector_store import QdrantStore, SearchPoint, VectorStore


class MockAsyncVectorStore(VectorStore):
    """Test double for async vector store."""

    def __init__(self):
        self.upserted_points = []
        self.search_queries = []

    def upsert(self, collection_name: str, points: list[dict]) -> bool:
        return True

    def search(
        self,
        collection_name: str,
        query_vector: list[float],
        limit: int = 5
    ) -> list[SearchPoint]:
        return []

    async def upsert_async(self, collection_name: str, points: list[dict]) -> bool:
        self.upserted_points.extend(points)
        return True

    async def search_async(
        self,
        collection_name: str,
        query_vector: list[float],
        limit: int = 5
    ) -> list[SearchPoint]:
        self.search_queries.append((query_vector, limit))
        return [
            SearchPoint(
                id="async-test-id",
                score=0.95,
                payload={"path": "async-test.md", "content": "async test content"}
            )
        ]

    def health_check(self) -> bool:
        return True

    def get_collection_info(self) -> dict:
        return {"collections": []}


@pytest.fixture
def anyio_backend():
    """Configure anyio backend for async tests."""
    return "asyncio"


class TestAsyncVectorStore:
    """Tests for async vector store methods."""

    @pytest.mark.asyncio
    async def test_vector_store_search_async(self):
        """VectorStore search_async returns search results."""
        mock_store = MockAsyncVectorStore()
        query_vector = [0.1] * 768

        results = await mock_store.search_async(
            collection_name="test_collection",
            query_vector=query_vector,
            limit=5
        )

        assert len(results) == 1
        assert results[0].id == "async-test-id"
        assert results[0].score == 0.95
        assert results[0].payload["path"] == "async-test.md"

    @pytest.mark.asyncio
    async def test_vector_store_upsert_async(self):
        """VectorStore upsert_async stores points successfully."""
        mock_store = MockAsyncVectorStore()
        points = [
            {
                "id": "test-1",
                "vector": [0.1] * 768,
                "payload": {"path": "test.md", "content": "test content"}
            }
        ]

        result = await mock_store.upsert_async(
            collection_name="test_collection",
            points=points
        )

        assert result is True
        assert len(mock_store.upserted_points) == 1
        assert mock_store.upserted_points[0]["id"] == "test-1"

    @pytest.mark.asyncio
    async def test_qdrant_store_search_async(self):
        """QdrantStore search_async delegates to async client."""
        with patch("qdrant_client.QdrantClient") as MockQdrantClient:
            mock_client = AsyncMock()
            MockQdrantClient.return_value = mock_client

            # Mock the search result
            mock_point = Mock()
            mock_point.id = "qdrant-test-id"
            mock_point.score = 0.89
            mock_point.payload = {"path": "qdrant-test.md", "content": "qdrant content"}
            mock_point.vector = None
            mock_client.search = AsyncMock(return_value=[mock_point])

            store = QdrantStore(url="http://localhost:6333")
            query_vector = [0.1] * 768

            results = await store.search_async(
                collection_name="test_collection",
                query_vector=query_vector,
                limit=5
            )

            assert len(results) == 1
            assert results[0].id == "qdrant-test-id"
            assert results[0].score == 0.89
            mock_client.search.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_qdrant_store_upsert_async(self):
        """QdrantStore upsert_async delegates to async client."""
        with patch("qdrant_client.QdrantClient") as MockQdrantClient:
            mock_client = AsyncMock()
            MockQdrantClient.return_value = mock_client

            # Mock upsert result
            mock_result = Mock()
            mock_result.status = "completed"
            mock_client.upsert = AsyncMock(return_value=mock_result)

            store = QdrantStore(url="http://localhost:6333")
            points = [
                {
                    "id": "test-1",
                    "vector": [0.1] * 768,
                    "payload": {"path": "test.md", "content": "test content"}
                }
            ]

            result = await store.upsert_async(
                collection_name="test_collection",
                points=points
            )

            assert result is True
            mock_client.upsert.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_qdrant_store_upsert_async_failed(self):
        """QdrantStore upsert_async returns False on failed status."""
        with patch("qdrant_client.QdrantClient") as MockQdrantClient:
            mock_client = AsyncMock()
            MockQdrantClient.return_value = mock_client

            # Mock failed upsert result
            mock_result = Mock()
            mock_result.status = "failed"
            mock_client.upsert = AsyncMock(return_value=mock_result)

            store = QdrantStore(url="http://localhost:6333")
            points = [
                {
                    "id": "test-1",
                    "vector": [0.1] * 768,
                    "payload": {"path": "test.md", "content": "test content"}
                }
            ]

            result = await store.upsert_async(
                collection_name="test_collection",
                points=points
            )

            assert result is False
