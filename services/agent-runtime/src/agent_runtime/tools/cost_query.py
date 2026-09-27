"""Cost query tool for GCP billing analysis."""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any

from .base import BaseTool, ToolScope

logger = logging.getLogger(__name__)


class CostQueryTool(BaseTool):
    """Queries GCP Cloud Billing data for cost analysis and anomaly detection."""

    @property
    def name(self) -> str:
        return "cost_query"

    @property
    def description(self) -> str:
        return (
            "Query GCP Cloud Billing export data for cost breakdowns, trends, "
            "and anomaly detection by service and resource."
        )

    @property
    def scope(self) -> ToolScope:
        return ToolScope.READ_ONLY

    def invoke(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Query cost data for a project.

        Args:
            input_data: {
                project_id (str): GCP project ID,
                days (int): Analysis window in days (default 30),
                group_by (str): Grouping dimension (service|resource|sku),
            }

        Returns:
            Cost breakdown dict with service costs, trends, and anomalies.
        """
        project_id = input_data.get("project_id", "")
        if not project_id:
            raise ValueError("project_id is required")

        days = int(input_data.get("days", 30))
        group_by = input_data.get("group_by", "service")

        # In production, this queries BigQuery billing export table
        # SELECT service.description, sum(cost) as total_cost ...
        # FROM `billing_project.billing_dataset.gcp_billing_export_v1_*`
        # WHERE usage_start_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL @days DAY)
        # GROUP BY service.description

        # Return structured cost data for now
        return self._get_cost_data(project_id, days, group_by)

    def _get_cost_data(
        self, project_id: str, days: int, group_by: str
    ) -> dict[str, Any]:
        """Build cost data structure."""
        end_date = datetime.now(tz=timezone.utc)
        start_date = end_date - timedelta(days=days)

        services = {
            "Compute Engine": {
                "current_cost": 450.00,
                "previous_cost": 380.00,
                "change_pct": 18.4,
                "trend": "increasing",
            },
            "Cloud SQL": {
                "current_cost": 280.00,
                "previous_cost": 275.00,
                "change_pct": 1.8,
                "trend": "stable",
            },
            "Google Kubernetes Engine": {
                "current_cost": 320.00,
                "previous_cost": 295.00,
                "change_pct": 8.5,
                "trend": "increasing",
            },
            "Cloud Storage": {
                "current_cost": 45.00,
                "previous_cost": 44.00,
                "change_pct": 2.3,
                "trend": "stable",
            },
            "Vertex AI": {
                "current_cost": 180.00,
                "previous_cost": 120.00,
                "change_pct": 50.0,
                "trend": "increasing",
            },
        }

        total = sum(v["current_cost"] for v in services.values())
        anomalies = [
            {"service": svc, "change_pct": data["change_pct"], "alert_threshold": 30.0}
            for svc, data in services.items()
            if data["change_pct"] > 30.0
        ]

        return {
            "project_id": project_id,
            "period_start": start_date.isoformat(),
            "period_end": end_date.isoformat(),
            "period_days": days,
            "services": services,
            "total_cost": total,
            "anomalies": anomalies,
            "group_by": group_by,
        }
