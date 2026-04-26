"""Service health check implementation."""
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from src.services.llm_provider import LLMProvider
from src.services.vector_store import VectorStore


class ServiceStatus(str, Enum):
    """Service health status values."""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class HealthStatus:
    """Health status for all services."""
    ollama: ServiceStatus
    qdrant: ServiceStatus
    ollama_error: Optional[str] = None
    qdrant_error: Optional[str] = None

    @property
    def is_healthy(self) -> bool:
        """True if both services are healthy."""
        return self.ollama == ServiceStatus.HEALTHY and self.qdrant == ServiceStatus.HEALTHY

    def to_dict(self) -> dict:
        """Convert to dictionary for API response."""
        return {
            "ollama": self.ollama.value,
            "qdrant": self.qdrant.value,
            "is_healthy": self.is_healthy,
            "ollama_error": self.ollama_error,
            "qdrant_error": self.qdrant_error,
        }


class HealthService:
    """Service for checking health of external dependencies."""

    def __init__(
        self,
        ollama_provider: Optional[LLMProvider] = None,
        vector_store: Optional[VectorStore] = None,
        qdrant_url: str = "http://localhost:6333"
    ):
        """Initialize health service.

        Args:
            ollama_provider: LLM provider instance (creates default if None)
            vector_store: Vector store instance (creates default if None)
            qdrant_url: Qdrant server URL (used if vector_store not provided)
        """
        self._ollama_provider = ollama_provider
        self._vector_store = vector_store
        self._qdrant_url = qdrant_url

    def _check_ollama(self) -> tuple[ServiceStatus, Optional[str]]:
        """Check Ollama service health via the LLM provider."""
        try:
            if self._ollama_provider:
                healthy = self._ollama_provider.health_check()
            else:
                import ollama
                ollama.list()
                healthy = True
            return ServiceStatus.HEALTHY if healthy else ServiceStatus.UNHEALTHY, None
        except Exception as e:
            return ServiceStatus.UNHEALTHY, str(e)

    def _check_qdrant(self) -> tuple[ServiceStatus, Optional[str]]:
        """Check Qdrant service health.

        Returns:
            Tuple of (status, error_message)
        """
        from qdrant_client import QdrantClient

        try:
            client = QdrantClient(url=self._qdrant_url)
            client.get_collections()
            return ServiceStatus.HEALTHY, None
        except Exception as e:
            return ServiceStatus.UNHEALTHY, str(e)

    def get_qdrant_info(self) -> dict:
        """Get Qdrant collection information.

        Returns:
            Dictionary with collection info
        """
        from qdrant_client import QdrantClient

        client = QdrantClient(url=self._qdrant_url)
        collections_response = client.get_collections()

        collections_info = []
        for collection in collections_response.collections:
            collections_info.append({
                "name": collection.name,
                "points_count": collection.points_count if hasattr(collection, "points_count") else None,
                "vectors_count": collection.vectors_count if hasattr(collection, "vectors_count") else None,
            })

        return {"collections": collections_info}

    def check_all(self) -> HealthStatus:
        """Check health of all services.

        Returns:
            HealthStatus with status of all services
        """
        ollama_status, ollama_error = self._check_ollama()
        qdrant_status, qdrant_error = self._check_qdrant()

        return HealthStatus(
            ollama=ollama_status,
            qdrant=qdrant_status,
            ollama_error=ollama_error,
            qdrant_error=qdrant_error,
        )
