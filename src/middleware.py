"""Rate limiting middleware for the Personal Wiki Chat application."""
import time
from collections import defaultdict
from typing import Dict, List

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.responses import JSONResponse


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware to rate limit requests per client IP.

    Args:
        max_requests: Maximum number of requests allowed within the time window (default: 10)
        window_seconds: Time window in seconds (default: 60)
    """

    def __init__(self, app, max_requests: int = 10, window_seconds: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        # Track requests: {ip: [timestamp1, timestamp2, ...]}
        self._request_history: Dict[str, List[float]] = defaultdict(list)

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request.

        Uses X-Forwarded-For header if present (for proxied requests),
        otherwise falls back to client.host.

        Args:
            request: The FastAPI request object

        Returns:
            Client IP address as a string
        """
        # Check X-Forwarded-For header (may contain multiple IPs, take the first)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # X-Forwarded-For can be comma-separated list of IPs
            # The first IP is the original client
            return forwarded_for.split(",")[0].strip()

        # Fall back to direct client host
        if request.client and request.client.host:
            return request.client.host

        return "unknown"

    def _is_rate_limited(self, ip: str) -> bool:
        """Check if an IP is currently rate limited.

        Updates the request history by removing expired entries and
        adding the current request timestamp.

        Args:
            ip: Client IP address

        Returns:
            True if the IP has exceeded the rate limit, False otherwise
        """
        current_time = time.time()
        window_start = current_time - self.window_seconds

        # Remove expired entries (older than window)
        self._request_history[ip] = [
            ts for ts in self._request_history[ip]
            if ts > window_start
        ]

        # Check if rate limited
        if len(self._request_history[ip]) >= self.max_requests:
            return True

        # Record this request
        self._request_history[ip].append(current_time)
        return False

    async def dispatch(self, request: Request, call_next):
        """Process incoming requests and enforce rate limiting.

        Args:
            request: The incoming FastAPI request
            call_next: Function to call the next middleware/handler

        Returns:
            JSONResponse with 429 status if rate limited,
            otherwise the response from call_next
        """
        client_ip = self._get_client_ip(request)

        if self._is_rate_limited(client_ip):
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "detail": f"Maximum {self.max_requests} requests per {self.window_seconds} seconds"
                }
            )

        # Not rate limited, proceed with request
        return await call_next(request)
