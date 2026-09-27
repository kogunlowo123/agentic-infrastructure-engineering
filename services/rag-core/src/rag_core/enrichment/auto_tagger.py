"""Auto-tagger for Terraform resource types and cloud services."""

import logging
import re

logger = logging.getLogger(__name__)

# Common GCP Terraform resource prefixes
GCP_RESOURCE_PREFIXES = [
    "google_compute_",
    "google_container_",
    "google_storage_",
    "google_sql_",
    "google_pubsub_",
    "google_kms_",
    "google_iam_",
    "google_cloud_run_",
    "google_bigquery_",
    "google_logging_",
    "google_monitoring_",
    "google_artifact_registry_",
    "google_secret_manager_",
]

RESOURCE_TYPE_PATTERN = re.compile(r'resource\s+"([^"]+)"')
MODULE_PATTERN = re.compile(r'module\s+"([^"]+)"')


class AutoTagger:
    """Automatically tags chunks with Terraform resource types and cloud services."""

    def __init__(self, use_llm: bool = False, model: str = "vertex_ai/gemini-1.5-flash") -> None:
        self._use_llm = use_llm
        self._model = model

    def tag(self, content: str, metadata: dict) -> dict:
        """Extract Terraform resource types and add tags.

        Args:
            content: Document text to analyze.
            metadata: Existing metadata to update.

        Returns:
            Updated metadata with resource_types and cloud_services.
        """
        resource_types = self._extract_resource_types(content)
        cloud_services = self._classify_cloud_services(resource_types)

        metadata["resource_types"] = resource_types
        metadata["cloud_services"] = cloud_services
        metadata["is_terraform"] = bool(resource_types)

        if self._use_llm and resource_types:
            try:
                tags = self._llm_tag(content)
                metadata["llm_tags"] = tags
            except Exception as exc:
                logger.warning("LLM tagging failed: %s", exc)

        return metadata

    def _extract_resource_types(self, content: str) -> list[str]:
        """Extract Terraform resource type identifiers."""
        return list(set(RESOURCE_TYPE_PATTERN.findall(content)))

    def _classify_cloud_services(self, resource_types: list[str]) -> list[str]:
        """Map resource types to cloud service categories."""
        services: set[str] = set()
        for rt in resource_types:
            for prefix in GCP_RESOURCE_PREFIXES:
                if rt.startswith(prefix):
                    service = prefix.replace("google_", "").rstrip("_")
                    services.add(f"gcp/{service}")
                    break
        return list(services)

    def _llm_tag(self, content: str) -> list[str]:
        """Use LLM to generate semantic tags."""
        import litellm  # type: ignore[import]

        response = litellm.completion(
            model=self._model,
            messages=[
                {
                    "role": "user",
                    "content": (
                        "List 3-5 short tags for this Terraform code. "
                        "Respond with comma-separated tags only.\n\n"
                        + content[:500]
                    ),
                }
            ],
            max_tokens=64,
            temperature=0.0,
        )
        tags_str = response.choices[0].message.content.strip()
        return [t.strip() for t in tags_str.split(",") if t.strip()]
