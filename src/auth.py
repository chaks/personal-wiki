"""API key authentication middleware."""
import os
import secrets
from typing import Optional, Set

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


def generate_api_key() -> str:
    """Generate a secure random API key.

    Returns:
        A secure random API key string (32 bytes hex-encoded = 64 characters).
    """
    return secrets.token_hex(32)


def load_api_keys_from_env() -> Set[str]:
    """Load API keys from WIKI_API_KEYS environment variable.

    The environment variable should contain comma-separated API keys.
    Whitespace around keys is stripped.

    Returns:
        Set of API keys, or empty set if not configured.
    """
    api_keys_str = os.environ.get("WIKI_API_KEYS", "")
    if not api_keys_str.strip():
        return set()

    return {key.strip() for key in api_keys_str.split(",") if key.strip()}


class APIKeyAuthMiddleware(BaseHTTPMiddleware):
    """Middleware for API key authentication.

    Checks for X-API-Key header on all requests except excluded paths.
    Returns 401 Unauthorized for missing or invalid API keys.
    """

    def __init__(
        self,
        app,
        api_keys: Set[str],
        exclude_paths: Optional[Set[str]] = None,
    ):
        """Initialize the middleware.

        Args:
            app: The ASGI application.
            api_keys: Set of valid API keys.
            exclude_paths: Set of paths to exclude from authentication.
                Defaults to /health, /docs, /openapi.json.
        """
        super().__init__(app)
        self.api_keys = api_keys
        self.exclude_paths = exclude_paths or {"/health", "/docs", "/openapi.json"}

    async def dispatch(self, request: Request, call_next) -> Response:
        """Process the request and check API key authentication.

        Args:
            request: The incoming request.
            call_next: The next middleware or application handler.

        Returns:
            Response from the application or 401 Unauthorized.
        """
        # Bypass authentication for excluded paths
        if request.url.path in self.exclude_paths:
            return await call_next(request)

        # If no API keys configured, allow all requests
        if not self.api_keys:
            return await call_next(request)

        # Check for API key in header
        api_key = request.headers.get("X-API-Key")

        if not api_key:
            return Response(
                content="Missing API key",
                status_code=401,
                media_type="text/plain",
            )

        if api_key not in self.api_keys:
            return Response(
                content="Invalid API key",
                status_code=401,
                media_type="text/plain",
            )

        # API key is valid, proceed with request
        return await call_next(request)
