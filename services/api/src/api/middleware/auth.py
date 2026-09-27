"""JWT authentication middleware."""

from __future__ import annotations

import logging
import os
from typing import Awaitable, Callable

import jwt
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

EXCLUDED_PATHS = {"/api/v1/health", "/api/v1/readiness", "/docs", "/openapi.json", "/redoc"}


class JWTAuthMiddleware(BaseHTTPMiddleware):
    """Validates Bearer JWT tokens on all protected routes."""

    def __init__(self, app, secret_key: str | None = None) -> None:
        super().__init__(app)
        self._secret_key = secret_key or os.getenv("JWT_SECRET_KEY", "dev-secret-key")
        self._algorithm = os.getenv("JWT_ALGORITHM", "HS256")

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """Authenticate requests and populate user context."""
        if request.url.path in EXCLUDED_PATHS or request.url.path.startswith("/docs"):
            return await call_next(request)

        auth_header = request.headers.get("Authorization", "")

        if not auth_header:
            return JSONResponse(
                status_code=401,
                content={"detail": "Authorization header missing"},
            )

        if not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid authorization scheme. Use Bearer"},
            )

        token = auth_header[len("Bearer "):]

        try:
            payload = jwt.decode(
                token,
                self._secret_key,
                algorithms=[self._algorithm],
                options={"verify_exp": True},
            )
            request.state.user_id = payload.get("sub", "")
            request.state.tenant_id = payload.get("tenant_id", "default")
            request.state.scopes = payload.get("scopes", [])
        except jwt.ExpiredSignatureError:
            return JSONResponse(
                status_code=401,
                content={"detail": "Token has expired"},
            )
        except jwt.InvalidTokenError as exc:
            logger.debug("Invalid JWT: %s", exc)
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid token"},
            )

        return await call_next(request)
