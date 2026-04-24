"""Vector store abstraction for external service decoupling."""
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, AsyncIterator, Optional

logger = logging.getLogger(__name__)


@dataclass
class SearchPoint:
    """A search result point."""
    id: Any
    score: float
    payload: dict
    vector: Optional[list[float]] = None


class VectorStore(ABC):
    """Abstract interface for vector stores."""

    @abstractmethod
    def upsert(self, collection_name: str, points: list[dict]) -> bool:
        """Upsert points into the collection.

        Args:
            collection_name: Name of the collection
            points: List of points to upsert

        Returns:
            True if successful
        """
        pass

    @abstractmethod
    def search(
        self,
        collection_name: str,
        query_vector: list[float],
        limit: int = 5
    ) -> list[SearchPoint]:
        """Search for similar points.

        Args:
            collection_name: Name of the collection
            query_vector: Query embedding vector
            limit: Maximum results to return

        Returns:
            List of search results
        """
        pass

    @abstractmethod
    def health_check(self) -> bool:
        """Check if the vector store is healthy.

        Returns:
            True if the store is healthy, False otherwise
        """
        pass

    @abstractmethod
    def get_collection_info(self) -> dict:
        """Get information about collections.

        Returns:
            Dictionary with collection information
        """
        pass

    @abstractmethod
    async def search_async(
        self,
        collection_name: str,
        query_vector: list[float],
        limit: int = 5
    ) -> list[SearchPoint]:
        """Asynchronously search for similar points.

        Args:
            collection_name: Name of the collection
            query_vector: Query embedding vector
            limit: Maximum results to return

        Returns:
            List of search results
        """
        pass

    @abstractmethod
    async def upsert_async(self, collection_name: str, points: list[dict]) -> bool:
        """Asynchronously upsert points into the collection.

        Args:
            collection_name: Name of the collection
            points: List of points to upsert

        Returns:
            True if successful
        """
        pass


class QdrantStore(VectorStore):
    """Qdrant implementation of vector store."""

    def __init__(self, url: str = "http://localhost:6333"):
        """Initialize Qdrant client.

        Args:
            url: Qdrant server URL (default: http://localhost:6333)
        """
        from qdrant_client import QdrantClient

        self.client = QdrantClient(url=url)
        self.url = url
        logger.debug(f"QdrantStore initialized with url: {url}")

    def upsert(self, collection_name: str, points: list[dict]) -> bool:
        """Upsert points into Qdrant collection."""
        logger.debug(f"Upserting {len(points)} points into {collection_name}")
        result = self.client.upsert(
            collection_name=collection_name,
            points=points
        )
        return result.status == "completed"

    def search(
        self,
        collection_name: str,
        query_vector: list[float],
        limit: int = 5
    ) -> list[SearchPoint]:
        """Search for similar points in Qdrant."""
        logger.debug(f"Searching {collection_name} with limit={limit}")
        results = self.client.search(
            collection_name=collection_name,
            query_vector=query_vector,
            limit=limit
        )
        return [
            SearchPoint(
                id=r.id,
                score=r.score,
                payload=r.payload or {},
                vector=r.vector if hasattr(r, "vector") else None
            )
            for r in results
        ]

    def health_check(self) -> bool:
        """Check if Qdrant service is available."""
        try:
            self.client.get_collections()
            return True
        except Exception as e:
            logger.error(f"Qdrant health check failed: {e}")
            return False

    def get_collection_info(self) -> dict:
        """Get information about Qdrant collections.

        Returns:
            Dictionary with collection information
        """
        collections_response = self.client.get_collections()

        collections_info = []
        for collection in collections_response.collections:
            collections_info.append({
                "name": collection.name,
                "points_count": getattr(collection, "points_count", None),
                "vectors_count": getattr(collection, "vectors_count", None),
            })

        return {"collections": collections_info}

    async def search_async(
        self,
        collection_name: str,
        query_vector: list[float],
        limit: int = 5
    ) -> list[SearchPoint]:
        """Asynchronously search for similar points in Qdrant."""
        logger.debug(f"Async searching {collection_name} with limit={limit}")
        results = await self.client.search(
            collection_name=collection_name,
            query_vector=query_vector,
            limit=limit
        )
        return [
            SearchPoint(
                id=r.id,
                score=r.score,
                payload=r.payload or {},
                vector=r.vector if hasattr(r, "vector") else None
            )
            for r in results
        ]

    async def upsert_async(self, collection_name: str, points: list[dict]) -> bool:
        """Asynchronously upsert points into Qdrant collection."""
        logger.debug(f"Async upserting {len(points)} points into {collection_name}")
        result = await self.client.upsert(
            collection_name=collection_name,
            points=points
        )
        return result.status == "completed"
