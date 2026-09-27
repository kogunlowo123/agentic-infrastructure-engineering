"""Budget enforcer for platform gateway.

Tracks token and dollar spend per tenant. Blocks requests when monthly
budget is exceeded. Emits alerts at configurable thresholds.
"""

from __future__ import annotations

import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from threading import Lock
from typing import Any

logger = logging.getLogger(__name__)

# Cost per 1M tokens (approximate, USD)
_COST_PER_1M_INPUT: dict[str, float] = {
    "vertex_ai/gemini-1.5-pro": 3.50,
    "vertex_ai/gemini-1.5-flash": 0.35,
}
_COST_PER_1M_OUTPUT: dict[str, float] = {
    "vertex_ai/gemini-1.5-pro": 10.50,
    "vertex_ai/gemini-1.5-flash": 1.05,
}


@dataclass
class TenantBudget:
    tenant_id: str
    monthly_limit_usd: float
    alert_threshold_pct: float = 80.0
    hard_cutoff_pct: float = 100.0
    spend_usd: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    reset_at: float = field(default_factory=lambda: _next_month_reset())


def _next_month_reset() -> float:
    """Return Unix timestamp of the start of next month."""
    import calendar
    import datetime

    now = datetime.datetime.utcnow()
    if now.month == 12:
        next_month = datetime.datetime(now.year + 1, 1, 1)
    else:
        next_month = datetime.datetime(now.year, now.month + 1, 1)
    return next_month.timestamp()


class BudgetEnforcer:
    """Thread-safe budget tracker and enforcer per tenant."""

    def __init__(self, default_monthly_limit_usd: float = 500.0) -> None:
        self._default_limit = default_monthly_limit_usd
        self._budgets: dict[str, TenantBudget] = {}
        self._lock = Lock()

    def check_allowed(self, tenant_id: str) -> tuple[bool, str]:
        """Check if tenant is within budget.

        Returns (allowed, reason). Resets spend if month has rolled over.
        """
        with self._lock:
            budget = self._get_or_create(tenant_id)
            self._maybe_reset(budget)

            pct = (budget.spend_usd / budget.monthly_limit_usd) * 100 if budget.monthly_limit_usd > 0 else 0

            if pct >= budget.hard_cutoff_pct:
                return False, f"Monthly budget exhausted: ${budget.spend_usd:.2f} / ${budget.monthly_limit_usd:.2f}"

            if pct >= budget.alert_threshold_pct:
                logger.warning(
                    "Budget alert tenant=%s spend=%.2f limit=%.2f pct=%.1f",
                    tenant_id, budget.spend_usd, budget.monthly_limit_usd, pct,
                )

            return True, "ok"

    def record_usage(self, tenant_id: str, model: str, input_tokens: int, output_tokens: int) -> float:
        """Record token usage and return cost in USD."""
        cost_in = (input_tokens / 1_000_000) * _COST_PER_1M_INPUT.get(model, 1.0)
        cost_out = (output_tokens / 1_000_000) * _COST_PER_1M_OUTPUT.get(model, 3.0)
        total_cost = cost_in + cost_out

        with self._lock:
            budget = self._get_or_create(tenant_id)
            budget.spend_usd += total_cost
            budget.input_tokens += input_tokens
            budget.output_tokens += output_tokens

        return total_cost

    def get_usage(self, tenant_id: str) -> dict[str, Any]:
        with self._lock:
            budget = self._get_or_create(tenant_id)
            return {
                "tenant_id": tenant_id,
                "spend_usd": budget.spend_usd,
                "monthly_limit_usd": budget.monthly_limit_usd,
                "input_tokens": budget.input_tokens,
                "output_tokens": budget.output_tokens,
                "utilization_pct": (budget.spend_usd / budget.monthly_limit_usd * 100)
                if budget.monthly_limit_usd > 0 else 0.0,
            }

    def _get_or_create(self, tenant_id: str) -> TenantBudget:
        if tenant_id not in self._budgets:
            self._budgets[tenant_id] = TenantBudget(
                tenant_id=tenant_id,
                monthly_limit_usd=self._default_limit,
            )
        return self._budgets[tenant_id]

    def _maybe_reset(self, budget: TenantBudget) -> None:
        if time.time() >= budget.reset_at:
            budget.spend_usd = 0.0
            budget.input_tokens = 0
            budget.output_tokens = 0
            budget.reset_at = _next_month_reset()
