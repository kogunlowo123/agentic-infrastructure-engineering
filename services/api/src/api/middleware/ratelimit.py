"""Rate limiting middleware — 100 requests/minute per tenant."""

from __future__ import annotations

import logging
import time
from collections import defaultdict, deque
from typing import Awaitable, Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Sliding window rate limiter — 100 requests/minute per tenant."""

    def __init__(self, app, requests_per_minute: int = 100) -> None:
        super().__init__(app)
        self._limit = requests_per_minute
        self._window = 60.0  # seconds
        self._buckets: dict[str, deque] = defaultdict(deque)

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """Apply rate limiting per tenant."""
        tenant_id = getattr(request.state, "tenant_id", "default")
        now = time.monotonic()
        window_start = now - self._window

        bucket = self._buckets[tenant_id]

        # Remove expired entries
        while bucket and bucket[0] < window_start:
            bucket.popleft()

        if len(bucket) >= self._limit:
            retry_after = int(bucket[0] + self._window - now) + 1
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Try again later."},
                headers={"Retry-After": str(retry_after)},
            )

        bucket.append(now)
        return await call_next(request)
