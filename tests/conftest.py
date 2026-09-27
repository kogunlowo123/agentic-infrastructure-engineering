"""Shared pytest fixtures for all test suites."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient


@pytest.fixture
def mock_settings():
    """Mock application settings."""
    settings = MagicMock()
    settings.database_url = "postgresql://test:test@localhost:5432/test"
    settings.opensearch_url = "http://localhost:9200"
    settings.embedding_model = "BAAI/bge-large-en-v1.5"
    settings.gcp_project_id = "test-project"
    settings.chunk_size = 512
    settings.chunk_overlap = 64
    settings.top_k = 10
    settings.rerank_top_k = 3
    return settings


@pytest.fixture
def sample_hcl() -> str:
    """A valid Terraform HCL string for a GCS bucket."""
    return '''terraform {
  required_version = ">= 1.8"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

resource "google_storage_bucket" "test_bucket" {
  name          = "test-project-test-bucket"
  project       = "test-project"
  location      = "us-central1"
  storage_class = "STANDARD"

  uniform_bucket_level_access = true

  versioning {
    enabled = true
  }

  labels = {
    environment = "dev"
    managed-by  = "terraform"
  }
}
'''


@pytest.fixture
def sample_iac_request() -> dict:
    """Sample IaC generation request payload."""
    return {
        "resource_type": "google_storage_bucket",
        "cloud": "gcp",
        "environment": "dev",
        "config": {
            "name": "test_bucket",
            "bucket_name": "test-project-test-bucket",
            "location": "us-central1",
        },
        "project_id": "test-project",
    }


@pytest.fixture
def mock_checkov_output() -> str:
    """Mock checkov JSON output with no findings."""
    return json.dumps({
        "results": {
            "passed_checks": [
                {
                    "check_id": "CKV_GCP_29",
                    "check_name": "Ensure that Cloud Storage bucket have uniform bucket-level access enabled",
                    "resource": "google_storage_bucket.test_bucket",
                }
            ],
            "failed_checks": [],
        }
    })


@pytest.fixture
def mock_checkov_output_with_findings() -> str:
    """Mock checkov JSON output with HIGH finding."""
    return json.dumps({
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


@pytest.fixture
def mock_llm_hcl_response(sample_hcl: str):
    """Mock LiteLLM completion that returns valid HCL."""
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = sample_hcl
    return mock_response


@pytest.fixture
def sample_drift_state_equal() -> dict:
    """State that equals the plan — no drift."""
    return {
        "resource_changes": [
            {
                "address": "google_storage_bucket.my_bucket",
                "change": {
                    "actions": ["no-op"],
                    "before": {"name": "my-bucket", "location": "us-central1"},
                    "after": {"name": "my-bucket", "location": "us-central1"},
                },
            }
        ]
    }


@pytest.fixture
def sample_drift_state_changed() -> dict:
    """State with one changed resource — single drift item."""
    return {
        "resource_changes": [
            {
                "address": "google_storage_bucket.my_bucket",
                "change": {
                    "actions": ["update"],
                    "before": {"name": "my-bucket", "location": "us-east1"},
                    "after": {"name": "my-bucket", "location": "us-central1"},
                },
            }
        ]
    }


@pytest.fixture
def test_app():
    """FastAPI test application."""
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../services/api/src"))
    from api.main import app
    return app


@pytest.fixture
def test_client(test_app):
    """Synchronous test client for the API."""
    with TestClient(test_app) as client:
        yield client
