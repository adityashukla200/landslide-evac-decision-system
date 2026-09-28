"""In-memory sliding-window rate limiting middleware for FastAPI."""

import time
from collections import defaultdict, deque
from typing import Dict, Deque
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Sliding-window in-memory rate limiter per client IP address."""

    def __init__(self, app, requests_per_minute: int = 180):
        super().__init__(app)
        self.limit = requests_per_minute
        self.window_seconds = 60.0
        self.clients: Dict[str, Deque[float]] = defaultdict(deque)

    async def dispatch(self, request: Request, call_next) -> Response:
        # Exclude static docs or internal health endpoints from aggressive rate-limiting
        if request.url.path in ("/health", "/docs", "/redoc", "/openapi.json"):
            return await call_next(request)

        client_ip = request.client.host if request.client else "127.0.0.1"
        now = time.time()
        window_start = now - self.window_seconds

        timestamps = self.clients[client_ip]

        # Purge timestamps older than 60s
        while timestamps and timestamps[0] < window_start:
            timestamps.popleft()

        if len(timestamps) >= self.limit:
            retry_after = int(self.window_seconds - (now - timestamps[0])) + 1
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "detail": f"Maximum {self.limit} requests per minute. Please retry after {retry_after} seconds.",
                    "client_ip": client_ip,
                },
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(self.limit),
                    "X-RateLimit-Remaining": "0",
                },
            )

        timestamps.append(now)
        remaining = self.limit - len(timestamps)

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self.limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response
