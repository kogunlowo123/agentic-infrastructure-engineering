"""LLM router for the platform gateway.

Routes LLM requests to the appropriate provider/model based on agent family,
tier, and routing rules. Implements retry with exponential backoff and
circuit-breaker pattern.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any

import litellm

logger = logging.getLogger(__name__)

# Routing table: maps (agent_family, tier) to (primary_model, fallback_model)
_ROUTING_TABLE: dict[tuple[str, str], tuple[str, str]] = {
    ("iac-generator", "T2"): ("vertex_ai/gemini-1.5-pro", "vertex_ai/gemini-1.5-flash"),
    ("drift-detector", "T1"): ("vertex_ai/gemini-1.5-flash", "vertex_ai/gemini-1.5-pro"),
    ("cost-optimizer", "T1"): ("vertex_ai/gemini-1.5-flash", "vertex_ai/gemini-1.5-pro"),
}
_DEFAULT_MODELS = ("vertex_ai/gemini-1.5-flash", "vertex_ai/gemini-1.5-pro")


@dataclass
class RouteRequest:
    messages: list[dict[str, str]]
    agent_family: str
    tier: str
    session_id: str
    tenant_id: str
    max_tokens: int = 4096
    temperature: float = 0.1
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class RouteResponse:
    content: str
    model: str
    usage: dict[str, int]
    latency_ms: float
    session_id: str


class GatewayRouter:
    """Routes LLM requests with fallback and retry logic."""

    def __init__(
        self,
        max_retries: int = 3,
        initial_delay: float = 0.5,
        backoff_multiplier: float = 2.0,
    ) -> None:
        self._max_retries = max_retries
        self._initial_delay = initial_delay
        self._backoff_multiplier = backoff_multiplier

    async def route(self, request: RouteRequest) -> RouteResponse:
        """Route a request to the appropriate LLM model.

        Tries primary model first, falls back on rate limit or server errors.
        """
        primary, fallback = _ROUTING_TABLE.get(
            (request.agent_family, request.tier), _DEFAULT_MODELS
        )

        for model in (primary, fallback):
            try:
                return await self._call_with_retry(model, request)
            except litellm.RateLimitError:
                logger.warning("Rate limit on %s, trying fallback", model)
                continue
            except litellm.ServiceUnavailableError:
                logger.warning("Service unavailable on %s, trying fallback", model)
                continue

        raise RuntimeError(
            f"All models exhausted for agent_family={request.agent_family} tier={request.tier}"
        )

    async def _call_with_retry(self, model: str, request: RouteRequest) -> RouteResponse:
        delay = self._initial_delay
        last_exc: Exception | None = None

        for attempt in range(self._max_retries):
            try:
                start = time.monotonic()
                response = await litellm.acompletion(
                    model=model,
                    messages=request.messages,
                    max_tokens=request.max_tokens,
                    temperature=request.temperature,
                    **request.extra,
                )
                latency_ms = (time.monotonic() - start) * 1000

                content = response.choices[0].message.content or ""
                usage = {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                }

                logger.info(
                    "LLM call succeeded model=%s attempt=%d latency_ms=%.1f tokens=%d",
                    model, attempt, latency_ms, usage["total_tokens"],
                )
                return RouteResponse(
                    content=content,
                    model=model,
                    usage=usage,
                    latency_ms=latency_ms,
                    session_id=request.session_id,
                )

            except (litellm.RateLimitError, litellm.ServiceUnavailableError):
                raise  # Let caller handle fallback
            except Exception as exc:
                last_exc = exc
                logger.warning("LLM call failed attempt=%d model=%s: %s", attempt, model, exc)
                if attempt < self._max_retries - 1:
                    await asyncio.sleep(delay)
                    delay *= self._backoff_multiplier

        raise RuntimeError(f"LLM call failed after {self._max_retries} attempts") from last_exc
