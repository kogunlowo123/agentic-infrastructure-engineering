"""FastAPI application entry point for the Agentic Infrastructure Engineering API."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .middleware.auth import JWTAuthMiddleware
from .middleware.ratelimit import RateLimitMiddleware
from .middleware.tenant import TenantMiddleware
from .middleware.tracing import TracingMiddleware
from .routes.v1 import cost, drift, health, iac

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan: startup and shutdown events."""
    logger.info("Starting Agentic Infrastructure Engineering API v0.1.0")
    yield
    logger.info("Shutting down API")


app = FastAPI(
    title="Agentic Infrastructure Engineering API",
    description=(
        "Enterprise AI platform for automated Terraform IaC generation, "
        "infrastructure drift detection, and cloud cost optimization."
    ),
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Middleware (applied in reverse order)
app.add_middleware(TracingMiddleware)
app.add_middleware(RateLimitMiddleware, requests_per_minute=100)
app.add_middleware(TenantMiddleware)
app.add_middleware(JWTAuthMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type", "X-Tenant-ID", "X-Trace-ID"],
)

# Routes
app.include_router(health.router, prefix="/api/v1")
app.include_router(iac.router, prefix="/api/v1")
app.include_router(drift.router, prefix="/api/v1")
app.include_router(cost.router, prefix="/api/v1")


@app.exception_handler(404)
async def not_found_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content={"detail": f"Path {request.url.path!r} not found"},
    )


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error for %s", request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )
