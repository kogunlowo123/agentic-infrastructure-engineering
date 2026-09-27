"""Tenant context middleware."""

from __future__ import annotations

import logging
from typing import Awaitable, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class TenantMiddleware(BaseHTTPMiddleware):
    """Extracts and validates tenant context from request headers."""

    DEFAULT_TENANT = "default"

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """Extract tenant ID from headers and populate request state."""
        tenant_id = request.headers.get("X-Tenant-ID") or getattr(
            request.state, "tenant_id", self.DEFAULT_TENANT
        )

        if not tenant_id:
            tenant_id = self.DEFAULT_TENANT

        request.state.tenant_id = tenant_id
        response = await call_next(request)
        response.headers["X-Tenant-ID"] = tenant_id
        return response
