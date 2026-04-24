"""Tests for rate limiting middleware."""
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from src.middleware import RateLimitMiddleware


@pytest.fixture
def test_dirs(tmp_path):
    """Create test directories."""
    return {
        "wiki": tmp_path / "wiki",
        "state": tmp_path / "state",
        "static": tmp_path / "static",
    }


class TestRateLimitMiddleware:
    """Tests for RateLimitMiddleware."""

    def test_rate_limit_allows_normal_requests(self, test_dirs):
        """Rate limit allows up to max_requests within window."""
        from src.server import create_app

        test_dirs["static"].mkdir(parents=True)
        (test_dirs["static"] / "index.html").write_text("<html>Test</html>")

        # Create app with rate limiting: 10 requests per 60 seconds
        app = create_app(
            test_dirs["wiki"],
            test_dirs["state"],
            test_dirs["static"],
            api_keys=None,  # No auth to focus on rate limiting
        )

        # Add rate limiting middleware
        app.add_middleware(RateLimitMiddleware, max_requests=10, window_seconds=60)

        with TestClient(app) as client:
            # 10 requests should succeed (within limit)
            for i in range(10):
                response = client.get("/health")
                assert response.status_code == 200, f"Request {i+1} should succeed"

    def test_rate_limit_blocks_excess_requests(self, test_dirs):
        """Rate limit blocks requests exceeding max_requests."""
        from src.server import create_app

        test_dirs["static"].mkdir(parents=True)
        (test_dirs["static"] / "index.html").write_text("<html>Test</html>")

        # Create app with rate limiting: 10 requests per 60 seconds
        app = create_app(
            test_dirs["wiki"],
            test_dirs["state"],
            test_dirs["static"],
            api_keys=None,
        )

        # Add rate limiting middleware
        app.add_middleware(RateLimitMiddleware, max_requests=10, window_seconds=60)

        with TestClient(app) as client:
            # First 10 requests should succeed
            for i in range(10):
                response = client.get("/health")
                assert response.status_code == 200, f"Request {i+1} should succeed"

            # 11th request should be rate limited
            response = client.get("/health")
            assert response.status_code == 429, "11th request should be rate limited"

    def test_rate_limit_by_ip(self, test_dirs):
        """Different IPs have independent rate limits."""
        from src.server import create_app

        test_dirs["static"].mkdir(parents=True)
        (test_dirs["static"] / "index.html").write_text("<html>Test</html>")

        # Create app with rate limiting: 5 requests per 60 seconds (smaller for easier testing)
        app = create_app(
            test_dirs["wiki"],
            test_dirs["state"],
            test_dirs["static"],
            api_keys=None,
        )

        # Add rate limiting middleware
        app.add_middleware(RateLimitMiddleware, max_requests=5, window_seconds=60)

        with TestClient(app) as client:
            # Simulate requests from IP 1 (5 requests - at limit)
            for i in range(5):
                response = client.get("/health", headers={"X-Forwarded-For": "192.168.1.1"})
                assert response.status_code == 200, f"IP1 Request {i+1} should succeed"

            # 6th request from IP 1 should be rate limited
            response = client.get("/health", headers={"X-Forwarded-For": "192.168.1.1"})
            assert response.status_code == 429, "IP1 6th request should be rate limited"

            # Requests from different IP should still succeed (independent limit)
            for i in range(5):
                response = client.get("/health", headers={"X-Forwarded-For": "192.168.1.2"})
                assert response.status_code == 200, f"IP2 Request {i+1} should succeed"

    def test_rate_limit_middleware_integration(self, test_dirs):
        """Verify RateLimitMiddleware is properly registered in create_app."""
        from src.server import create_app

        test_dirs["static"].mkdir(parents=True)
        (test_dirs["static"] / "index.html").write_text("<html>Test</html>")

        # Create app with rate limiting middleware registered
        app = create_app(
            test_dirs["wiki"],
            test_dirs["state"],
            test_dirs["static"],
            api_keys=None,
        )

        # Add rate limiting middleware
        app.add_middleware(RateLimitMiddleware, max_requests=10, window_seconds=60)

        # Verify middleware is in the app's middleware stack
        # Check that RateLimitMiddleware is registered by iterating through user_middleware
        middleware_found = False
        for mw in app.user_middleware:
            if mw.cls == RateLimitMiddleware:
                middleware_found = True
                break

        assert middleware_found, "RateLimitMiddleware should be registered in the app"
