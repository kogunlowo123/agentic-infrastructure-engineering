"""Unit tests for infrastructure drift detection."""

from __future__ import annotations

import sys
import os

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../services/agent-runtime/src"))


class TestDriftDetection:
    """Tests for drift detection logic."""

    def test_no_drift_detected(self, sample_drift_state_equal):
        """No drift when state matches plan."""
        from agent_runtime.orchestrator.graph import compare_state_plan
        from agent_runtime.orchestrator.state import DriftDetectionState

        state: DriftDetectionState = {
            "resource_ids": [],
            "project_id": "test-project",
            "terraform_plan_json": sample_drift_state_equal,
            "current_state": {},
            "drift_report": {},
            "drifted_resources": [],
            "severity": "none",
            "session_id": "test-session",
            "error": None,
        }

        result = compare_state_plan(state)

        assert result["drift_report"]["total_drifted"] == 0
        assert result["severity"] == "none"

    def test_drift_detected_single_resource(self, sample_drift_state_changed):
        """Drift should be detected when resource attribute changes."""
        from agent_runtime.orchestrator.graph import compare_state_plan
        from agent_runtime.orchestrator.state import DriftDetectionState

        state: DriftDetectionState = {
            "resource_ids": [],
            "project_id": "test-project",
            "terraform_plan_json": sample_drift_state_changed,
            "current_state": {},
            "drift_report": {},
            "drifted_resources": [],
            "severity": "none",
            "session_id": "test-session",
            "error": None,
        }

        result = compare_state_plan(state)

        assert result["drift_report"]["total_drifted"] >= 1
        assert result["severity"] != "none"
        items = result["drift_report"]["items"]
        assert any(item["attribute"] == "location" for item in items)

    def test_drift_severity_classification_security(self):
        """Security-related attribute drift should be classified as critical or high."""
        from agent_runtime.orchestrator.graph import _classify_drift_severity

        severity = _classify_drift_severity("google_compute_firewall.my_rule", "firewall_policy")
        assert severity in ("critical", "high")

    def test_drift_severity_classification_tag(self):
        """Tag changes should be low severity."""
        from agent_runtime.orchestrator.graph import _classify_drift_severity

        severity = _classify_drift_severity("google_storage_bucket.my_bucket", "labels")
        assert severity == "low"

    def test_overall_severity_critical_wins(self):
        """Overall severity should be the highest individual severity."""
        from agent_runtime.orchestrator.graph import _compute_overall_severity

        drifted = [
            {"severity": "low"},
            {"severity": "critical"},
            {"severity": "medium"},
        ]
        assert _compute_overall_severity(drifted) == "critical"

    def test_overall_severity_empty(self):
        """Empty drift list should result in 'none' severity."""
        from agent_runtime.orchestrator.graph import _compute_overall_severity

        assert _compute_overall_severity([]) == "none"

    def test_multiple_drifted_resources(self):
        """Multiple drifted resources should all appear in the report."""
        from agent_runtime.orchestrator.graph import compare_state_plan
        from agent_runtime.orchestrator.state import DriftDetectionState

        plan_json = {
            "resource_changes": [
                {
                    "address": "google_storage_bucket.bucket_a",
                    "change": {
                        "actions": ["update"],
                        "before": {"location": "us-east1"},
                        "after": {"location": "us-central1"},
                    },
                },
                {
                    "address": "google_storage_bucket.bucket_b",
                    "change": {
                        "actions": ["update"],
                        "before": {"storage_class": "NEARLINE"},
                        "after": {"storage_class": "STANDARD"},
                    },
                },
            ]
        }

        state: DriftDetectionState = {
            "resource_ids": [],
            "project_id": "test-project",
            "terraform_plan_json": plan_json,
            "current_state": {},
            "drift_report": {},
            "drifted_resources": [],
            "severity": "none",
            "session_id": "test-session",
            "error": None,
        }

        result = compare_state_plan(state)
        assert result["drift_report"]["total_drifted"] >= 2
