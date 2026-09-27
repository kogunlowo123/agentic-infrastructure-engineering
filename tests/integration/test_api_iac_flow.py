"""Integration tests for IaC API flow."""

from __future__ import annotations

import sys
import os
import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../services/api/src"))


def _make_jwt(tenant_id: str = "test-tenant") -> str:
    """Create a signed JWT for testing."""
    import jwt

    payload = {
        "sub": "test-user",
        "tenant_id": tenant_id,
        "scopes": ["iac:generate"],
        "exp": 9999999999,
    }
    return jwt.encode(payload, "dev-secret-key", algorithm="HS256")


def _mock_agent_response(pr_url: str = "https://github.com/test/repo/pull/1") -> dict:
    return {
        "state": {
            "generated_hcl": 'resource "google_storage_bucket" "test" { name = "test" }',
            "security_scan": {
                "passed": True,
                "findings": [],
                "severity_counts": {},
            },
            "pr_url": pr_url,
            "pr_number": 1,
            "approval_status": "pending",
        }
    }


class TestIaCAPIFlow:
    """Integration tests for POST /api/v1/iac/generate."""

    def test_generate_iac_endpoint(self, test_client):
        """POST /iac/generate should return 202 with pr_url and session_id."""
        token = _make_jwt()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = _mock_agent_response()
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            response = test_client.post(
                "/api/v1/iac/generate",
                json={
                    "resource_type": "google_storage_bucket",
                    "cloud": "gcp",
                    "environment": "dev",
                    "config": {"name": "test_bucket"},
                    "project_id": "test-project",
                },
                headers={"Authorization": f"Bearer {token}"},
            )

        assert response.status_code in (200, 202)
        data = response.json()
        assert "session_id" in data
        assert "hcl_preview" in data
        assert "security_scan_result" in data

    def test_generate_requires_auth(self, test_client):
        """POST /iac/generate without Authorization header should return 401."""
        response = test_client.post(
            "/api/v1/iac/generate",
            json={
                "resource_type": "google_storage_bucket",
                "cloud": "gcp",
                "environment": "dev",
                "config": {},
                "project_id": "test-project",
            },
        )
        assert response.status_code == 401

    def test_generate_invalid_token(self, test_client):
        """POST /iac/generate with invalid token should return 401."""
        response = test_client.post(
            "/api/v1/iac/generate",
            json={
                "resource_type": "google_storage_bucket",
                "cloud": "gcp",
                "environment": "dev",
                "config": {},
                "project_id": "test-project",
            },
            headers={"Authorization": "Bearer invalid-token-here"},
        )
        assert response.status_code == 401

    def test_health_endpoint(self, test_client):
        """GET /health should return 200 with status ok."""
        response = test_client.get("/api/v1/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    def test_drift_endpoint(self, test_client):
        """POST /drift/detect should return 200 with DriftReport."""
        token = _make_jwt()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "state": {
                "drift_report": {
                    "total_drifted": 0,
                    "items": [],
                    "severity": "none",
                    "recommendations": [],
                },
                "severity": "none",
            }
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            response = test_client.post(
                "/api/v1/drift/detect",
                json={
                    "project_id": "test-project",
                    "terraform_plan_json": {},
                    "resource_ids": [],
                },
                headers={"Authorization": f"Bearer {token}"},
            )

        assert response.status_code == 200
        data = response.json()
        assert "total_drifted" in data
        assert "severity" in data
