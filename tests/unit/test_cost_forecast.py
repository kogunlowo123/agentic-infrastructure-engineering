"""Unit tests for cost forecasting and optimization."""

from __future__ import annotations

import sys
import os

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../services/agent-runtime/src"))


class TestCostForecast:
    """Tests for cost optimization graph logic."""

    def test_forecast_returns_delta(self):
        """Cost forecast should compute delta between current and projected."""
        from agent_runtime.orchestrator.graph import (
            analyze_cost_patterns,
            fetch_cost_data,
        )
        from agent_runtime.orchestrator.state import CostOptimizationState

        state: CostOptimizationState = {
            "analysis_period_days": 30,
            "project_id": "test-project",
            "include_recommendations": True,
            "cost_data": {},
            "recommendations": [],
            "estimated_savings_usd": 0.0,
            "current_monthly_usd": 0.0,
            "projected_monthly_usd": 0.0,
            "session_id": "test-session",
            "error": None,
        }

        fetched = fetch_cost_data(state)
        state.update(fetched)

        analyzed = analyze_cost_patterns(state)

        assert "estimated_savings_usd" in analyzed
        assert "projected_monthly_usd" in analyzed
        assert analyzed["estimated_savings_usd"] >= 0.0

        current = state["current_monthly_usd"]
        projected = analyzed["projected_monthly_usd"]
        savings = analyzed["estimated_savings_usd"]

        assert abs((current - projected) - savings) < 0.01

    def test_recommendations_generated_for_increasing_costs(self):
        """Recommendations should be generated for services with increasing trends."""
        from agent_runtime.orchestrator.graph import analyze_cost_patterns
        from agent_runtime.orchestrator.state import CostOptimizationState

        state: CostOptimizationState = {
            "analysis_period_days": 30,
            "project_id": "test-project",
            "include_recommendations": True,
            "cost_data": {
                "services": {
                    "Compute Engine": {"monthly_cost": 500.0, "trend": "increasing"},
                    "Cloud Storage": {"monthly_cost": 50.0, "trend": "stable"},
                }
            },
            "recommendations": [],
            "estimated_savings_usd": 0.0,
            "current_monthly_usd": 550.0,
            "projected_monthly_usd": 550.0,
            "session_id": "test-session",
            "error": None,
        }

        result = analyze_cost_patterns(state)

        assert len(result["recommendations"]) > 0
        rec_resources = [r["resource_id"] for r in result["recommendations"]]
        assert any("compute" in r.lower() for r in rec_resources)

    def test_no_recommendations_for_stable_costs(self):
        """No recommendations should be generated for all-stable cost trends."""
        from agent_runtime.orchestrator.graph import analyze_cost_patterns
        from agent_runtime.orchestrator.state import CostOptimizationState

        state: CostOptimizationState = {
            "analysis_period_days": 30,
            "project_id": "test-project",
            "include_recommendations": True,
            "cost_data": {
                "services": {
                    "Cloud Storage": {"monthly_cost": 50.0, "trend": "stable"},
                    "Cloud SQL": {"monthly_cost": 100.0, "trend": "stable"},
                }
            },
            "recommendations": [],
            "estimated_savings_usd": 0.0,
            "current_monthly_usd": 150.0,
            "projected_monthly_usd": 150.0,
            "session_id": "test-session",
            "error": None,
        }

        result = analyze_cost_patterns(state)
        assert result["estimated_savings_usd"] == 0.0

    def test_cost_query_tool_returns_structured_data(self):
        """CostQueryTool should return structured cost data."""
        from agent_runtime.tools.cost_query import CostQueryTool

        tool = CostQueryTool()
        result = tool.invoke({"project_id": "test-project", "days": 30})

        assert result["project_id"] == "test-project"
        assert "services" in result
        assert "total_cost" in result
        assert result["total_cost"] > 0

    def test_cost_query_requires_project_id(self):
        """CostQueryTool should raise ValueError for missing project_id."""
        from agent_runtime.tools.cost_query import CostQueryTool

        tool = CostQueryTool()
        with pytest.raises(ValueError, match="project_id is required"):
            tool.invoke({})
