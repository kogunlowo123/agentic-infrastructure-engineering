"""Token budget management for agent sessions."""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from typing import ClassVar

logger = logging.getLogger(__name__)


class BudgetExceeded(Exception):
    """Raised when a session's token budget is exceeded."""


@dataclass
class SessionBudget:
    """Tracks token usage for a single session."""

    session_id: str
    max_tokens: int
    used_tokens: int = 0
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def consume(self, tokens: int) -> None:
        """Record token usage. Raises BudgetExceeded if limit reached."""
        with self._lock:
            if self.used_tokens + tokens > self.max_tokens:
                raise BudgetExceeded(
                    f"Session {self.session_id}: token budget exceeded "
                    f"({self.used_tokens + tokens} > {self.max_tokens})"
                )
            self.used_tokens += tokens

    @property
    def remaining(self) -> int:
        return max(0, self.max_tokens - self.used_tokens)

    @property
    def utilization(self) -> float:
        return self.used_tokens / self.max_tokens if self.max_tokens > 0 else 0.0


class TokenBudgetManager:
    """Manages per-session token budgets."""

    TIER_DEFAULTS: ClassVar[dict[str, int]] = {
        "T1": 32768,
        "T2": 131072,
    }

    def __init__(self) -> None:
        self._sessions: dict[str, SessionBudget] = {}
        self._lock = threading.Lock()

    def create_session(
        self,
        session_id: str,
        tier: str = "T1",
        max_tokens: int | None = None,
    ) -> SessionBudget:
        """Create a new budget for a session."""
        budget = max_tokens or self.TIER_DEFAULTS.get(tier, 32768)
        with self._lock:
            session_budget = SessionBudget(
                session_id=session_id,
                max_tokens=budget,
            )
            self._sessions[session_id] = session_budget
        return session_budget

    def consume(self, session_id: str, tokens: int) -> None:
        """Record token usage for a session."""
        budget = self._sessions.get(session_id)
        if budget is None:
            logger.warning("No budget found for session %s, creating T1 default", session_id)
            budget = self.create_session(session_id)
        budget.consume(tokens)

    def get_session(self, session_id: str) -> SessionBudget | None:
        """Return the budget for a session."""
        return self._sessions.get(session_id)

    def release_session(self, session_id: str) -> None:
        """Remove session budget."""
        with self._lock:
            self._sessions.pop(session_id, None)
