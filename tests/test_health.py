"""Tests for service health checks."""
import pytest
from unittest.mock import Mock, patch, MagicMock
from src.services.health import HealthService, ServiceStatus, HealthStatus


class TestServiceStatus:
    """Tests for ServiceStatus enum."""

    def test_service_status_enum_values(self):
        """ServiceStatus has correct enum values."""
        assert ServiceStatus.HEALTHY.value == "healthy"
        assert ServiceStatus.UNHEALTHY.value == "unhealthy"
        assert ServiceStatus.UNKNOWN.value == "unknown"


class TestHealthStatus:
    """Tests for HealthStatus dataclass."""

    def test_health_status_all_healthy(self):
        """HealthStatus with both services healthy."""
        status = HealthStatus(
            ollama=ServiceStatus.HEALTHY,
            qdrant=ServiceStatus.HEALTHY
        )
        assert status.is_healthy is True
        assert status.ollama_error is None
        assert status.qdrant_error is None

    def test_health_status_ollama_unhealthy(self):
        """HealthStatus with Ollama unhealthy."""
        status = HealthStatus(
            ollama=ServiceStatus.UNHEALTHY,
            qdrant=ServiceStatus.HEALTHY,
            ollama_error="Connection refused"
        )
        assert status.is_healthy is False
        assert status.ollama_error == "Connection refused"

    def test_health_status_qdrant_unhealthy(self):
        """HealthStatus with Qdrant unhealthy."""
        status = HealthStatus(
            ollama=ServiceStatus.HEALTHY,
            qdrant=ServiceStatus.UNHEALTHY,
            qdrant_error="Timeout"
        )
        assert status.is_healthy is False
        assert status.qdrant_error == "Timeout"

    def test_health_status_both_unhealthy(self):
        """HealthStatus with both services unhealthy."""
        status = HealthStatus(
            ollama=ServiceStatus.UNHEALTHY,
            qdrant=ServiceStatus.UNHEALTHY,
            ollama_error="Ollama down",
            qdrant_error="Qdrant down"
        )
        assert status.is_healthy is False

    def test_health_status_to_dict(self):
        """HealthStatus to_dict returns correct structure."""
        status = HealthStatus(
            ollama=ServiceStatus.HEALTHY,
            qdrant=ServiceStatus.HEALTHY
        )
        result = status.to_dict()
        assert result == {
            "ollama": "healthy",
            "qdrant": "healthy",
            "is_healthy": True,
            "ollama_error": None,
            "qdrant_error": None
        }

    def test_health_status_to_dict_with_errors(self):
        """HealthStatus to_dict includes errors."""
        status = HealthStatus(
            ollama=ServiceStatus.UNHEALTHY,
            qdrant=ServiceStatus.UNHEALTHY,
            ollama_error="Connection refused",
            qdrant_error="Timeout"
        )
        result = status.to_dict()
        assert result == {
            "ollama": "unhealthy",
            "qdrant": "unhealthy",
            "is_healthy": False,
            "ollama_error": "Connection refused",
            "qdrant_error": "Timeout"
        }


class TestHealthService:
    """Tests for HealthService."""

    @patch("ollama.list")
    @patch("qdrant_client.QdrantClient")
    def test_check_all_both_healthy(self, MockQdrantClient, mock_ollama_list):
        """HealthService.check_all returns healthy when both services are up."""
        # Mock Ollama
        mock_ollama_list.return_value = {"models": [{"name": "gemma4:e2b"}]}

        # Mock Qdrant
        mock_client = Mock()
        mock_collection = Mock(name="test_collection")
        mock_client.get_collections.return_value = Mock(collections=[mock_collection])
        MockQdrantClient.return_value = mock_client

        service = HealthService(
            ollama_provider=Mock(),  # We're testing via ollama.list directly
            vector_store=Mock()
        )

        # Replace internal check methods with mocked versions
        with patch.object(service, "_check_ollama", return_value=(ServiceStatus.HEALTHY, None)), \
             patch.object(service, "_check_qdrant", return_value=(ServiceStatus.HEALTHY, None)):
            status = service.check_all()

        assert status.ollama == ServiceStatus.HEALTHY
        assert status.qdrant == ServiceStatus.HEALTHY
        assert status.is_healthy is True

    @patch("ollama.list")
    def test_check_ollama_healthy(self, mock_ollama_list):
        """Ollama health check succeeds when service is available."""
        mock_ollama_list.return_value = {"models": [{"name": "gemma4:e2b"}]}

        service = HealthService()
        result_status, result_error = service._check_ollama()

        assert result_status == ServiceStatus.HEALTHY
        assert result_error is None
        mock_ollama_list.assert_called_once()

    @patch("ollama.list")
    def test_check_ollama_unhealthy(self, mock_ollama_list):
        """Ollama health check fails when service is unavailable."""
        mock_ollama_list.side_effect = Exception("Connection refused")

        service = HealthService()
        result_status, result_error = service._check_ollama()

        assert result_status == ServiceStatus.UNHEALTHY
        assert result_error == "Connection refused"

    @patch("qdrant_client.QdrantClient")
    def test_check_qdrant_healthy(self, MockQdrantClient):
        """Qdrant health check succeeds when service is available."""
        mock_client = Mock()
        mock_collection = Mock(name="test_collection")
        mock_client.get_collections.return_value = Mock(collections=[mock_collection])
        MockQdrantClient.return_value = mock_client

        service = HealthService()
        result_status, result_error = service._check_qdrant()

        assert result_status == ServiceStatus.HEALTHY
        assert result_error is None

    @patch("qdrant_client.QdrantClient")
    def test_check_qdrant_unhealthy(self, MockQdrantClient):
        """Qdrant health check fails when service is unavailable."""
        mock_client = Mock()
        mock_client.get_collections.side_effect = Exception("Timeout")
        MockQdrantClient.return_value = mock_client

        service = HealthService()
        result_status, result_error = service._check_qdrant()

        assert result_status == ServiceStatus.UNHEALTHY
        assert "Timeout" in result_error

    @patch("qdrant_client.QdrantClient")
    def test_get_collection_info(self, MockQdrantClient):
        """Qdrant get_collection_info returns collection details."""
        mock_client = Mock()
        mock_collection = Mock(
            name="test_collection",
            points_count=100,
            vectors_count=100
        )
        mock_client.get_collections.return_value = Mock(collections=[mock_collection])
        MockQdrantClient.return_value = mock_client

        service = HealthService()
        info = service.get_qdrant_info()

        assert "collections" in info
        assert len(info["collections"]) == 1

    def test_check_all_combined_status(self):
        """check_all returns combined status correctly."""
        service = HealthService()

        with patch.object(service, "_check_ollama", return_value=(ServiceStatus.HEALTHY, None)), \
             patch.object(service, "_check_qdrant", return_value=(ServiceStatus.UNHEALTHY, "Qdrant error")):
            status = service.check_all()

        assert status.ollama == ServiceStatus.HEALTHY
        assert status.qdrant == ServiceStatus.UNHEALTHY
        assert status.qdrant_error == "Qdrant error"
        assert status.is_healthy is False
