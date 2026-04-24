"""Vector store abstraction for external service decoupling."""
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional

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
