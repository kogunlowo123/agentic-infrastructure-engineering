"""Unit tests for Terraform IaC generation."""

from __future__ import annotations

import json
import subprocess
import sys
import os
from unittest.mock import MagicMock, patch

import pytest

# Add agent-runtime to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../services/agent-runtime/src"))


class TestTerraformGenerateTool:
    """Tests for TerraformGenerateTool."""

    def test_generates_valid_hcl(self, sample_iac_request, monkeypatch):
        """Generated HCL should be non-empty and contain resource block."""
        from agent_runtime.tools.terraform_generate import TerraformGenerateTool

        # Monkeypatch subprocess to avoid checkov dependency
        mock_result = MagicMock()
        mock_result.stdout = json.dumps({"results": {"passed_checks": [], "failed_checks": []}})
        mock_result.returncode = 0
        monkeypatch.setattr(subprocess, "run", lambda *a, **kw: mock_result)

        tool = TerraformGenerateTool()
        result = tool.invoke(sample_iac_request)

        assert result["hcl_content"]
        assert len(result["hcl_content"]) > 0
        assert "resource" in result["hcl_content"]

    def test_hcl_contains_required_resource_type(self, sample_iac_request, monkeypatch):
        """Generated HCL should contain the requested resource type."""
        from agent_runtime.tools.terraform_generate import TerraformGenerateTool

        mock_result = MagicMock()
        mock_result.stdout = json.dumps({"results": {"passed_checks": [], "failed_checks": []}})
        monkeypatch.setattr(subprocess, "run", lambda *a, **kw: mock_result)

        tool = TerraformGenerateTool()
        result = tool.invoke(sample_iac_request)

        assert "google_storage_bucket" in result["hcl_content"]

    def test_security_scan_runs(self, sample_iac_request, monkeypatch):
        """Security scan should run and return findings list."""
        from agent_runtime.tools.terraform_generate import TerraformGenerateTool

        mock_checkov_output = json.dumps({
            "results": {
                "passed_checks": [],
                "failed_checks": [
                    {
                        "check_id": "CKV_GCP_62",
                        "check_name": "Ensure Cloud Storage Bucket has access logs",
                        "severity": "HIGH",
                        "resource": "google_storage_bucket.test_bucket",
                        "file_path": "/tmp/main.tf",
                    }
                ],
            }
        })

        mock_result = MagicMock()
        mock_result.stdout = mock_checkov_output
        mock_result.returncode = 1
        monkeypatch.setattr(subprocess, "run", lambda *a, **kw: mock_result)

        tool = TerraformGenerateTool()
        result = tool.invoke(sample_iac_request)

        assert isinstance(result["security_findings"], list)
        assert len(result["security_findings"]) > 0
        assert result["security_findings"][0]["check_id"] == "CKV_GCP_62"

    def test_security_scan_not_found_graceful(self, sample_iac_request, monkeypatch):
        """Tool should still return HCL when checkov is not installed."""
        from agent_runtime.tools.terraform_generate import TerraformGenerateTool

        def raise_file_not_found(*args, **kwargs):
            raise FileNotFoundError("checkov not found")

        monkeypatch.setattr(subprocess, "run", raise_file_not_found)

        tool = TerraformGenerateTool()
        result = tool.invoke(sample_iac_request)

        assert result["hcl_content"]
        assert result["security_findings"] == []
        assert result["passed_security"] is True

    def test_pr_ready_flag_no_critical_findings(self, sample_iac_request, monkeypatch):
        """pr_ready should be True when no CRITICAL/HIGH findings."""
        from agent_runtime.tools.terraform_generate import TerraformGenerateTool

        mock_result = MagicMock()
        mock_result.stdout = json.dumps({
            "results": {
                "passed_checks": [],
                "failed_checks": [
                    {
                        "check_id": "CKV_GCP_63",
                        "check_name": "Low severity check",
                        "severity": "LOW",
                        "resource": "google_storage_bucket.test_bucket",
                    }
                ],
            }
        })
        monkeypatch.setattr(subprocess, "run", lambda *a, **kw: mock_result)

        tool = TerraformGenerateTool()
        result = tool.invoke(sample_iac_request)

        assert result["pr_ready"] is True

    def test_pr_ready_false_on_critical_findings(self, sample_iac_request, monkeypatch):
        """pr_ready should be False when CRITICAL findings exist."""
        from agent_runtime.tools.terraform_generate import TerraformGenerateTool

        mock_result = MagicMock()
        mock_result.stdout = json.dumps({
            "results": {
                "passed_checks": [],
                "failed_checks": [
                    {
                        "check_id": "CKV_GCP_99",
                        "check_name": "Critical security issue",
                        "severity": "CRITICAL",
                        "resource": "google_storage_bucket.test_bucket",
                    }
                ],
            }
        })
        monkeypatch.setattr(subprocess, "run", lambda *a, **kw: mock_result)

        tool = TerraformGenerateTool()
        result = tool.invoke(sample_iac_request)

        assert result["pr_ready"] is False

    def test_missing_resource_type_raises(self):
        """Missing resource_type should raise ValueError."""
        from agent_runtime.tools.terraform_generate import TerraformGenerateTool

        tool = TerraformGenerateTool()
        with pytest.raises(ValueError, match="resource_type is required"):
            tool.invoke({"cloud": "gcp", "project_id": "test"})

    def test_hcl_contains_provider_block(self, sample_iac_request, monkeypatch):
        """Generated HCL should contain a required_providers block."""
        from agent_runtime.tools.terraform_generate import TerraformGenerateTool

        mock_result = MagicMock()
        mock_result.stdout = "{}"
        monkeypatch.setattr(subprocess, "run", lambda *a, **kw: mock_result)

        tool = TerraformGenerateTool()
        result = tool.invoke(sample_iac_request)

        assert "required_providers" in result["hcl_content"]
        assert "google" in result["hcl_content"]
