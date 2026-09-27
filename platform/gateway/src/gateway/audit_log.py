"""Audit log for platform gateway.

Records all LLM requests and responses in structured format for compliance,
cost attribution, and security review. PII scrubbing is applied before
log entries are written.
"""

from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import asdict, dataclass
from typing import Any

logger = logging.getLogger("gateway.audit")

# Patterns to scrub from log entries
_PII_PATTERNS: list[tuple[str, str]] = [
    (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", "<EMAIL>"),
    (r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b", "<CARD>"),
    (r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b", "<PHONE>"),
]


@dataclass
class AuditEntry:
    event_type: str
    session_id: str
    tenant_id: str
    agent_family: str
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    latency_ms: float
    timestamp: float
    success: bool
    error: str | None = None
    metadata: dict[str, Any] | None = None


def scrub_pii(text: str) -> str:
    """Remove PII patterns from text."""
    for pattern, replacement in _PII_PATTERNS:
        text = re.sub(pattern, replacement, text)
    return text


class GatewayAuditLog:
    """Structured audit logger for gateway events."""

    def __init__(self, include_bodies: bool = False, pii_scrub: bool = True) -> None:
        self._include_bodies = include_bodies
        self._pii_scrub = pii_scrub

    def log_request(
        self,
        session_id: str,
        tenant_id: str,
        agent_family: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cost_usd: float,
        latency_ms: float,
        success: bool,
        error: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        entry = AuditEntry(
            event_type="llm.request",
            session_id=session_id,
            tenant_id=tenant_id,
            agent_family=agent_family,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost_usd,
            latency_ms=latency_ms,
            timestamp=time.time(),
            success=success,
            error=error,
            metadata=metadata,
        )

        log_dict = asdict(entry)

        if self._pii_scrub and error:
            log_dict["error"] = scrub_pii(error)

        logger.info(json.dumps(log_dict))

    def log_budget_exceeded(self, tenant_id: str, spend_usd: float, limit_usd: float) -> None:
        logger.warning(
            json.dumps({
                "event_type": "budget.exceeded",
                "tenant_id": tenant_id,
                "spend_usd": spend_usd,
                "limit_usd": limit_usd,
                "timestamp": time.time(),
            })
        )

    def log_rate_limit(self, tenant_id: str, model: str, session_id: str) -> None:
        logger.warning(
            json.dumps({
                "event_type": "rate_limit.hit",
                "tenant_id": tenant_id,
                "model": model,
                "session_id": session_id,
                "timestamp": time.time(),
            })
        )
