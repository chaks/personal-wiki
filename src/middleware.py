from __future__ import annotations
"""Rate limiting middleware for the Personal Wiki Chat application."""
import asyncio
import time
from collections import defaultdict
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.responses import JSONResponse

RATE_LIMIT_EXCEEDED_MSG = "Rate limit exceeded"
_CLEANUP_INTERVAL = 1000


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
        self._request_history: dict[str, list[float]] = defaultdict(list)
        self._lock: asyncio.Lock | None = None  # Created lazily
        self._cleanup_counter = 0

    def _get_lock(self) -> asyncio.Lock:
        """Get or create the asyncio lock lazily."""
        if self._lock is None:
            self._lock = asyncio.Lock()
        return self._lock

    def _cleanup(self) -> None:
        """Remove IPs with no recent entries to prevent unbounded memory growth."""
        stale_keys = [
            ip for ip, timestamps in self._request_history.items()
            if not timestamps
        ]
        for ip in stale_keys:
            del self._request_history[ip]

    def _maybe_cleanup(self) -> None:
        """Trigger cleanup periodically to prevent memory leaks."""
        self._cleanup_counter += 1
        if self._cleanup_counter >= _CLEANUP_INTERVAL or len(self._request_history) > _CLEANUP_INTERVAL:
            self._cleanup()
            self._cleanup_counter = 0

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

        async with self._get_lock():
            self._maybe_cleanup()
            rate_limited = self._is_rate_limited(client_ip)

        if rate_limited:
            return JSONResponse(
                status_code=429,
                content={
                    "error": RATE_LIMIT_EXCEEDED_MSG,
                    "detail": f"Maximum {self.max_requests} requests per {self.window_seconds} seconds"
                },
                headers={"Retry-After": str(self.window_seconds)},
            )

        # Not rate limited, proceed with request
        return await call_next(request)
