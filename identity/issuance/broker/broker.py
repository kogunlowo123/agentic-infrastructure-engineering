"""Identity broker for agent session issuance.

Issues short-lived credentials for agent sessions, validates tier eligibility,
and enforces TTL policies.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import time
import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentCredential:
    """Short-lived credential issued to an agent session."""

    session_id: str
    agent_id: str
    tenant_id: str
    tier: str
    scopes: list[str]
    issued_at: float
    expires_at: float
    token: str

    @property
    def is_expired(self) -> bool:
        return time.time() > self.expires_at

    def has_scope(self, scope: str) -> bool:
        return scope in self.scopes


@dataclass
class IssuanceRequest:
    agent_id: str
    tenant_id: str
    requested_scopes: list[str]
    metadata: dict[str, Any] = field(default_factory=dict)


class IdentityBroker:
    """Issues and validates agent session credentials.

    Validates scope eligibility against the registry, enforces tier constraints,
    and produces HMAC-signed tokens.
    """

    # Agent registry: maps agent_id to allowed scopes and tier
    _REGISTRY: dict[str, dict[str, Any]] = {
        "iac-generator": {
            "tier": "T2",
            "scopes": {"iac:generate", "iac:read", "git:pr_create", "git:pr_read"},
            "ttl_seconds": 3600,
        },
        "drift-detector": {
            "tier": "T1",
            "scopes": {"drift:detect", "drift:read"},
            "ttl_seconds": 1800,
        },
        "cost-optimizer": {
            "tier": "T1",
            "scopes": {"cost:forecast", "cost:read"},
            "ttl_seconds": 1800,
        },
    }

    def __init__(self, signing_key: str | None = None) -> None:
        self._signing_key = (signing_key or os.environ.get("IDENTITY_SIGNING_KEY", "dev-signing-key")).encode()

    def issue(self, request: IssuanceRequest) -> AgentCredential:
        """Issue a credential for an agent session.

        Raises ValueError if agent_id unknown or scopes not permitted.
        """
        registry_entry = self._REGISTRY.get(request.agent_id)
        if registry_entry is None:
            raise ValueError(f"Unknown agent_id: {request.agent_id}")

        allowed_scopes: set[str] = registry_entry["scopes"]
        requested = set(request.requested_scopes)
        unauthorized = requested - allowed_scopes
        if unauthorized:
            raise ValueError(f"Scopes not permitted for {request.agent_id}: {unauthorized}")

        session_id = str(uuid.uuid4())
        now = time.time()
        ttl = registry_entry["ttl_seconds"]
        expires_at = now + ttl

        token = self._sign_token(session_id, request.agent_id, request.tenant_id, expires_at)

        return AgentCredential(
            session_id=session_id,
            agent_id=request.agent_id,
            tenant_id=request.tenant_id,
            tier=registry_entry["tier"],
            scopes=list(requested),
            issued_at=now,
            expires_at=expires_at,
            token=token,
        )

    def validate(self, token: str, session_id: str, agent_id: str, tenant_id: str, expires_at: float) -> bool:
        """Validate a credential token.

        Returns True if signature is valid and not expired.
        """
        if time.time() > expires_at:
            return False
        expected = self._sign_token(session_id, agent_id, tenant_id, expires_at)
        return hmac.compare_digest(token, expected)

    def _sign_token(self, session_id: str, agent_id: str, tenant_id: str, expires_at: float) -> str:
        payload = f"{session_id}:{agent_id}:{tenant_id}:{expires_at:.3f}"
        sig = hmac.new(self._signing_key, payload.encode(), hashlib.sha256).hexdigest()
        return sig
