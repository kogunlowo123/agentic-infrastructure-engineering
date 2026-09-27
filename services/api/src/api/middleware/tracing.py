"""OpenTelemetry tracing middleware."""

from __future__ import annotations

import logging
import uuid
from typing import Awaitable, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class TracingMiddleware(BaseHTTPMiddleware):
    """Adds distributed tracing context to requests and responses."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """Inject trace context and add trace headers to responses."""
        trace_id = request.headers.get("X-Trace-ID") or str(uuid.uuid4())
        span_id = str(uuid.uuid4())[:16]

        request.state.trace_id = trace_id
        request.state.span_id = span_id

        import structlog  # type: ignore[import]

        # Fallback to regular logging if structlog not available
        try:
            logger_ctx = structlog.get_logger().bind(
                trace_id=trace_id,
                path=str(request.url.path),
                method=request.method,
            )
        except Exception:
            logger_ctx = logger

        response = await call_next(request)

        response.headers["X-Trace-ID"] = trace_id
        response.headers["X-Span-ID"] = span_id

        return response
