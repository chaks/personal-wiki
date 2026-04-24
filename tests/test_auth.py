"""Tests for API key authentication middleware."""
import pytest
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient

from src.auth import APIKeyAuthMiddleware, generate_api_key, load_api_keys_from_env


@pytest.fixture
def test_dirs(tmp_path):
    """Create test directories."""
    return {
        "wiki": tmp_path / "wiki",
        "state": tmp_path / "state",
        "static": tmp_path / "static",
    }


@pytest.fixture
def valid_api_key():
    """Generate a valid API key for testing."""
    return generate_api_key()


@pytest.fixture
def api_keys(valid_api_key):
    """Return a set of API keys for testing."""
    return {valid_api_key}


class TestGenerateApiKey:
    """Tests for generate_api_key function."""

    def test_generate_api_key_returns_string(self):
        """generate_api_key returns a string."""
        key = generate_api_key()
        assert isinstance(key, str)

    def test_generate_api_key_returns_unique_keys(self):
        """generate_api_key returns unique keys each call."""
        key1 = generate_api_key()
        key2 = generate_api_key()
        assert key1 != key2

    def test_generate_api_key_length(self):
        """generate_api_key returns key with sufficient length."""
        key = generate_api_key()
        assert len(key) >= 32


class TestLoadApiKeysFromEnv:
    """Tests for load_api_keys_from_env function."""

    def test_load_api_keys_from_env_single_key(self):
        """load_api_keys_from_env loads single API key."""
        test_key = "test-api-key-12345"
        with patch.dict("os.environ", {"WIKI_API_KEYS": test_key}):
            keys = load_api_keys_from_env()
            assert keys == {test_key}

    def test_load_api_keys_from_env_multiple_keys(self):
        """load_api_keys_from_env loads multiple comma-separated API keys."""
        key1 = "test-api-key-1"
        key2 = "test-api-key-2"
        key3 = "test-api-key-3"
        with patch.dict("os.environ", {"WIKI_API_KEYS": f"{key1},{key2},{key3}"}):
            keys = load_api_keys_from_env()
            assert keys == {key1, key2, key3}

    def test_load_api_keys_from_env_empty_env(self):
        """load_api_keys_from_env returns empty set when env var not set."""
        with patch.dict("os.environ", {}, clear=True):
            # Remove WIKI_API_KEYS if it exists
            keys = load_api_keys_from_env()
            assert keys == set()

    def test_load_api_keys_from_env_empty_string(self):
        """load_api_keys_from_env returns empty set when env var is empty string."""
        with patch.dict("os.environ", {"WIKI_API_KEYS": ""}):
            keys = load_api_keys_from_env()
            assert keys == set()

    def test_load_api_keys_from_env_strips_whitespace(self):
        """load_api_keys_from_env strips whitespace from keys."""
        key1 = "test-api-key-1"
        key2 = "test-api-key-2"
        with patch.dict("os.environ", {"WIKI_API_KEYS": f"  {key1}  ,  {key2}  "}):
            keys = load_api_keys_from_env()
            assert keys == {key1, key2}


class TestApiKeyAuthMiddleware:
    """Tests for APIKeyAuthMiddleware."""

    def test_middleware_rejects_requests_without_api_key(self, test_dirs, api_keys):
        """Middleware returns 401 for requests without API key."""
        from src.server import create_app

        test_dirs["static"].mkdir(parents=True)
        (test_dirs["static"] / "index.html").write_text("<html>Test</html>")

        app = create_app(
            test_dirs["wiki"],
            test_dirs["state"],
            test_dirs["static"],
            api_keys=api_keys,
        )

        with TestClient(app) as client:
            # /chat is a protected endpoint
            response = client.post("/chat", json={"message": "Hello"})
            assert response.status_code == 401

    def test_middleware_rejects_invalid_api_key(self, test_dirs, valid_api_key):
        """Middleware returns 401 for requests with invalid API key."""
        from src.server import create_app

        test_dirs["static"].mkdir(parents=True)
        (test_dirs["static"] / "index.html").write_text("<html>Test</html>")

        app = create_app(
            test_dirs["wiki"],
            test_dirs["state"],
            test_dirs["static"],
            api_keys={"some-other-key"},
        )

        with TestClient(app) as client:
            # /chat is a protected endpoint
            response = client.post("/chat", json={"message": "Hello"}, headers={"X-API-Key": valid_api_key})
            assert response.status_code == 401

    def test_middleware_accepts_valid_api_key(self, test_dirs, valid_api_key):
        """Middleware allows requests with valid API key."""
        from src.server import create_app

        test_dirs["static"].mkdir(parents=True)
        (test_dirs["static"] / "index.html").write_text("<html>Test</html>")

        app = create_app(
            test_dirs["wiki"],
            test_dirs["state"],
            test_dirs["static"],
            api_keys={valid_api_key},
        )

        with TestClient(app) as client:
            response = client.get("/health", headers={"X-API-Key": valid_api_key})
            assert response.status_code == 200
            assert response.json() == {"status": "ok"}

    def test_excluded_paths_bypass_auth_health(self, test_dirs):
        """Excluded paths like /health bypass authentication."""
        from src.server import create_app

        test_dirs["static"].mkdir(parents=True)
        (test_dirs["static"] / "index.html").write_text("<html>Test</html>")

        app = create_app(
            test_dirs["wiki"],
            test_dirs["state"],
            test_dirs["static"],
            api_keys={"some-key"},
        )

        with TestClient(app) as client:
            # /health should be accessible without API key
            response = client.get("/health")
            assert response.status_code == 200

    def test_excluded_paths_bypass_auth_docs(self, test_dirs):
        """Excluded paths like /docs bypass authentication."""
        from src.server import create_app

        test_dirs["static"].mkdir(parents=True)
        (test_dirs["static"] / "index.html").write_text("<html>Test</html>")

        app = create_app(
            test_dirs["wiki"],
            test_dirs["state"],
            test_dirs["static"],
            api_keys={"some-key"},
        )

        with TestClient(app) as client:
            # /docs should be accessible without API key
            response = client.get("/docs")
            assert response.status_code == 200

    def test_excluded_paths_bypass_auth_openapi(self, test_dirs):
        """Excluded paths like /openapi.json bypass authentication."""
        from src.server import create_app

        test_dirs["static"].mkdir(parents=True)
        (test_dirs["static"] / "index.html").write_text("<html>Test</html>")

        app = create_app(
            test_dirs["wiki"],
            test_dirs["state"],
            test_dirs["static"],
            api_keys={"some-key"},
        )

        with TestClient(app) as client:
            # /openapi.json should be accessible without API key
            response = client.get("/openapi.json")
            assert response.status_code == 200

    def test_protected_path_requires_auth(self, test_dirs, valid_api_key):
        """Protected paths require valid API key."""
        from src.server import create_app

        test_dirs["static"].mkdir(parents=True)
        (test_dirs["static"] / "index.html").write_text("<html>Test</html>")

        app = create_app(
            test_dirs["wiki"],
            test_dirs["state"],
            test_dirs["static"],
            api_keys={valid_api_key},
        )

        with TestClient(app) as client:
            # /chat requires API key
            response = client.post("/chat", json={"message": "Hello"})
            assert response.status_code == 401

            # With valid key, should work (will fail later due to no LLM, but auth passes)
            response = client.post(
                "/chat", json={"message": "Hello"}, headers={"X-API-Key": valid_api_key}
            )
            # Should not be 401 - might be other error due to missing LLM
            assert response.status_code != 401

    def test_middleware_no_api_keys_configured(self, test_dirs):
        """When no API keys configured, all requests pass through."""
        from src.server import create_app

        test_dirs["static"].mkdir(parents=True)
        (test_dirs["static"] / "index.html").write_text("<html>Test</html>")

        # Empty set means no auth required
        app = create_app(
            test_dirs["wiki"],
            test_dirs["state"],
            test_dirs["static"],
            api_keys=set(),
        )

        with TestClient(app) as client:
            response = client.get("/health")
            assert response.status_code == 200
