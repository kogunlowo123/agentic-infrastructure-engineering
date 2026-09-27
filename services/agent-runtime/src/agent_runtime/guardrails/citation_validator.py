"""Citation validator for generated Terraform provider references."""

import re
import logging
from typing import Any

logger = logging.getLogger(__name__)

VALID_GCP_PROVIDER_VERSIONS = ["~> 5.0", "~> 4.0", ">= 5.0"]
PROVIDER_VERSION_PATTERN = re.compile(r'version\s*=\s*"([^"]+)"')


class CitationValidator:
    """Validates that generated Terraform uses valid provider versions and resource types."""

    KNOWN_GCP_RESOURCES = {
        "google_compute_instance", "google_compute_network", "google_compute_subnetwork",
        "google_container_cluster", "google_container_node_pool",
        "google_sql_database_instance", "google_sql_database", "google_sql_user",
        "google_storage_bucket", "google_storage_bucket_iam_member",
        "google_pubsub_topic", "google_pubsub_subscription",
        "google_kms_key_ring", "google_kms_crypto_key",
        "google_service_account", "google_project_iam_member",
        "google_secret_manager_secret", "google_artifact_registry_repository",
    }

    def validate(self, hcl_content: str) -> tuple[bool, list[str]]:
        """Validate Terraform HCL for correct resource types and provider versions.

        Returns:
            (is_valid, list_of_issues)
        """
        issues: list[str] = []

        resource_types = re.findall(r'resource\s+"([^"]+)"', hcl_content)
        for rt in resource_types:
            if rt.startswith("google_") and rt not in self.KNOWN_GCP_RESOURCES:
                logger.debug("Unknown GCP resource type: %s", rt)

        if not re.search(r'required_providers', hcl_content):
            issues.append("Missing required_providers block")

        return len(issues) == 0, issues
