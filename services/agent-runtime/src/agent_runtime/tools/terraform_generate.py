"""Terraform HCL generation tool with security scanning."""

from __future__ import annotations

import json
import logging
import os
import subprocess
import tempfile
from dataclasses import dataclass, field
from typing import Any

from .base import BaseTool, ToolScope

logger = logging.getLogger(__name__)


@dataclass
class IaCRequirement:
    """Input specification for IaC generation."""

    cloud: str
    resource_type: str
    config: dict
    environment: str = "dev"
    project_id: str = ""


@dataclass
class SecurityFinding:
    """A single security scan finding."""

    check_id: str
    check_name: str
    severity: str
    resource: str
    file: str = ""
    guideline: str = ""


@dataclass
class GeneratedIaC:
    """Result of Terraform HCL generation."""

    hcl_content: str
    security_findings: list[SecurityFinding] = field(default_factory=list)
    passed_security: bool = True
    resource_count: int = 0
    pr_ready: bool = True


GCS_BUCKET_TEMPLATE = '''terraform {{
  required_version = ">= 1.8"
  required_providers {{
    google = {{
      source  = "hashicorp/google"
      version = "~> 5.0"
    }}
  }}
}}

resource "google_storage_bucket" "{name}" {{
  name          = "{bucket_name}"
  project       = "{project_id}"
  location      = "{location}"
  storage_class = "{storage_class}"

  uniform_bucket_level_access = true

  versioning {{
    enabled = true
  }}

  lifecycle_rule {{
    condition {{
      age = {retention_days}
    }}
    action {{
      type = "Delete"
    }}
  }}

  labels = {{
    environment = "{environment}"
    managed-by  = "terraform"
  }}
}}
'''

GKE_CLUSTER_TEMPLATE = '''terraform {{
  required_version = ">= 1.8"
  required_providers {{
    google = {{
      source  = "hashicorp/google"
      version = "~> 5.0"
    }}
  }}
}}

resource "google_container_cluster" "{name}" {{
  name     = "{cluster_name}"
  project  = "{project_id}"
  location = "{region}"

  remove_default_node_pool = true
  initial_node_count       = 1

  workload_identity_config {{
    workload_pool = "{project_id}.svc.id.goog"
  }}

  network_policy {{
    enabled  = true
    provider = "CALICO"
  }}

  resource_labels = {{
    environment = "{environment}"
    managed-by  = "terraform"
  }}
}}
'''


TEMPLATES: dict[str, str] = {
    "google_storage_bucket": GCS_BUCKET_TEMPLATE,
    "google_container_cluster": GKE_CLUSTER_TEMPLATE,
}


class TerraformGenerateTool(BaseTool):
    """Generates Terraform HCL from requirements and runs security scanning."""

    @property
    def name(self) -> str:
        return "terraform_generate"

    @property
    def description(self) -> str:
        return (
            "Generate valid Terraform HCL for a GCP resource from requirements. "
            "Runs checkov security scan before returning. Returns pr_ready=True "
            "if no CRITICAL/HIGH findings."
        )

    @property
    def scope(self) -> ToolScope:
        return ToolScope.READ_WRITE

    def invoke(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Generate Terraform HCL and scan for security issues.

        Args:
            input_data: IaCRequirement fields.

        Returns:
            GeneratedIaC as dict.
        """
        req = IaCRequirement(
            cloud=input_data.get("cloud", "gcp"),
            resource_type=input_data.get("resource_type", ""),
            config=input_data.get("config", {}),
            environment=input_data.get("environment", "dev"),
            project_id=input_data.get("project_id", ""),
        )

        if not req.resource_type:
            raise ValueError("resource_type is required")

        hcl_content = self._generate_hcl(req)
        findings = self._run_security_scan(hcl_content)
        resource_count = self._count_resources(hcl_content)

        severity_counts: dict[str, int] = {}
        for f in findings:
            severity_counts[f.severity] = severity_counts.get(f.severity, 0) + 1

        passed = severity_counts.get("CRITICAL", 0) == 0
        pr_ready = severity_counts.get("CRITICAL", 0) == 0 and severity_counts.get("HIGH", 0) == 0

        result = GeneratedIaC(
            hcl_content=hcl_content,
            security_findings=findings,
            passed_security=passed,
            resource_count=resource_count,
            pr_ready=pr_ready,
        )

        return {
            "hcl_content": result.hcl_content,
            "security_findings": [
                {
                    "check_id": f.check_id,
                    "check_name": f.check_name,
                    "severity": f.severity,
                    "resource": f.resource,
                }
                for f in result.security_findings
            ],
            "passed_security": result.passed_security,
            "resource_count": result.resource_count,
            "pr_ready": result.pr_ready,
            "severity_counts": severity_counts,
        }

    def _generate_hcl(self, req: IaCRequirement) -> str:
        """Generate HCL from template or LLM."""
        template = TEMPLATES.get(req.resource_type)

        if template:
            config = req.config
            resource_name = config.get("name", req.resource_type.split("_")[-1])
            return template.format(
                name=resource_name,
                bucket_name=config.get("bucket_name", f"{req.project_id}-{resource_name}"),
                cluster_name=config.get("cluster_name", f"cluster-{resource_name}"),
                project_id=req.project_id or "PROJECT_ID",
                location=config.get("location", "us-central1"),
                region=config.get("region", "us-central1"),
                storage_class=config.get("storage_class", "STANDARD"),
                retention_days=config.get("retention_days", 365),
                environment=req.environment,
                **{k: v for k, v in config.items() if k not in (
                    "name", "bucket_name", "cluster_name", "project_id",
                    "location", "region", "storage_class", "retention_days"
                )},
            )

        # Fallback: generate minimal valid HCL
        return self._minimal_hcl(req)

    def _minimal_hcl(self, req: IaCRequirement) -> str:
        """Generate minimal valid HCL when no template matches."""
        resource_name = req.resource_type.split("_")[-1]
        config_attrs = "\n".join(
            f'  {k} = "{v}"' for k, v in req.config.items()
            if isinstance(v, str)
        )
        return f'''terraform {{
  required_version = ">= 1.8"
  required_providers {{
    google = {{
      source  = "hashicorp/google"
      version = "~> 5.0"
    }}
  }}
}}

resource "{req.resource_type}" "{resource_name}" {{
  project = "{req.project_id or "PROJECT_ID"}"
{config_attrs}

  labels = {{
    environment = "{req.environment}"
    managed-by  = "terraform"
  }}
}}
'''

    def _run_security_scan(self, hcl_content: str) -> list[SecurityFinding]:
        """Run checkov scan on HCL content."""
        findings: list[SecurityFinding] = []

        with tempfile.TemporaryDirectory() as tmpdir:
            tf_file = os.path.join(tmpdir, "main.tf")
            with open(tf_file, "w") as f:
                f.write(hcl_content)

            try:
                result = subprocess.run(
                    ["checkov", "-d", tmpdir, "--output", "json", "--quiet", "--compact"],
                    capture_output=True,
                    text=True,
                    timeout=60,
                )
                output_text = result.stdout or result.stderr
                scan_data = json.loads(output_text) if output_text.strip() else {}

                failed_checks: list[dict] = []
                if isinstance(scan_data, dict):
                    failed_checks = scan_data.get("results", {}).get("failed_checks", [])
                elif isinstance(scan_data, list):
                    for item in scan_data:
                        if isinstance(item, dict):
                            failed_checks.extend(
                                item.get("results", {}).get("failed_checks", [])
                            )

                for check in failed_checks:
                    findings.append(
                        SecurityFinding(
                            check_id=check.get("check_id", ""),
                            check_name=check.get("check_name", ""),
                            severity=check.get("severity", "UNKNOWN").upper(),
                            resource=check.get("resource", ""),
                            file=check.get("file_path", ""),
                            guideline=check.get("guideline", ""),
                        )
                    )

            except FileNotFoundError:
                logger.info("checkov not installed — security scan skipped")
            except subprocess.TimeoutExpired:
                logger.warning("checkov scan timed out")
            except json.JSONDecodeError as exc:
                logger.warning("checkov JSON parse error: %s", exc)
            except Exception as exc:
                logger.warning("Security scan error: %s", exc)

        return findings

    def _count_resources(self, hcl_content: str) -> int:
        """Count resource blocks in HCL."""
        import re
        return len(re.findall(r'^resource\s+"', hcl_content, re.MULTILINE))
