"""Vertex AI provider integration for the platform gateway.

Wraps LiteLLM's Vertex AI adapter with GCP-specific configuration,
Workload Identity support, and quota tracking.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class VertexAIConfig:
    project: str
    location: str
    models: list[str]

    @classmethod
    def from_env(cls) -> "VertexAIConfig":
        project = os.environ.get("VERTEX_AI_PROJECT", "")
        if not project:
            raise ValueError("VERTEX_AI_PROJECT environment variable is required")
        return cls(
            project=project,
            location=os.environ.get("VERTEX_AI_LOCATION", "us-central1"),
            models=[
                "vertex_ai/gemini-1.5-pro",
                "vertex_ai/gemini-1.5-flash",
            ],
        )


def configure_litellm_vertex(config: VertexAIConfig) -> None:
    """Configure LiteLLM for Vertex AI.

    Sets the project and location so all vertex_ai/* model calls
    are routed to the correct GCP project. Workload Identity is used
    automatically when running on GKE (no explicit credentials needed).
    """
    import litellm

    litellm.vertex_project = config.project
    litellm.vertex_location = config.location


def get_vertex_model_params(model: str) -> dict:
    """Return default parameters for a Vertex AI model."""
    params: dict = {
        "vertex_ai/gemini-1.5-pro": {
            "max_tokens": 32768,
            "temperature": 0.1,
            "top_p": 0.95,
        },
        "vertex_ai/gemini-1.5-flash": {
            "max_tokens": 32768,
            "temperature": 0.1,
            "top_p": 0.95,
        },
    }
    return params.get(model, {})
