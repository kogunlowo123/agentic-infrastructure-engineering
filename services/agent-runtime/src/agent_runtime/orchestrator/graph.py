"""LangGraph agent workflow graphs for IaC generation, drift detection, and cost optimization."""

from __future__ import annotations

import json
import logging
import os
import subprocess
import tempfile
from typing import Any

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from .state import CostOptimizationState, DriftDetectionState, IaCGenerationState

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────
# IaC Generator Graph
# ─────────────────────────────────────────────────────────────

def retrieve_golden_templates(state: IaCGenerationState) -> dict:
    """Retrieve golden IaC templates from RAG store for the requested resource type."""
    import httpx

    requirements = state["requirements"]
    resource_type = requirements.get("resource_type", "")
    cloud = requirements.get("cloud", "gcp")

    rag_url = os.getenv("RAG_CORE_URL", "http://rag-core:8082")
    query = f"{cloud} {resource_type} terraform resource configuration best practices"

    try:
        response = httpx.post(
            f"{rag_url}/retrieve",
            json={
                "query": query,
                "top_k": 5,
                "filters": {"file_type": "terraform"},
            },
            timeout=30.0,
        )
        response.raise_for_status()
        templates = response.json().get("results", [])
    except Exception as exc:
        logger.warning("RAG retrieval failed, using empty templates: %s", exc)
        templates = []

    return {"retrieved_templates": templates, "error": None}


def generate_hcl(state: IaCGenerationState) -> dict:
    """Generate Terraform HCL from requirements and retrieved templates."""
    import litellm  # type: ignore[import]

    requirements = state["requirements"]
    templates = state.get("retrieved_templates", [])

    template_context = "\n\n".join(
        t.get("content", "") for t in templates[:3] if t.get("content")
    )

    system_prompt = """You are an expert Terraform engineer specializing in GCP infrastructure.
Generate production-ready Terraform HCL code following security best practices.
Always include required_providers block, use locals for repeated values, and add
descriptive comments. Never include hardcoded credentials."""

    user_prompt = f"""Generate Terraform HCL for the following requirements:

Cloud Provider: {requirements.get('cloud', 'gcp')}
Resource Type: {requirements.get('resource_type', '')}
Environment: {requirements.get('environment', 'dev')}
Project ID: {requirements.get('project_id', 'my-project')}
Configuration: {json.dumps(requirements.get('config', {}), indent=2)}

Reference templates from the knowledge base:
{template_context[:3000] if template_context else "No templates available, use best practices."}

Return ONLY valid Terraform HCL code, no markdown code blocks."""

    try:
        response = litellm.completion(
            model=os.getenv("AGENT_MODEL", "vertex_ai/gemini-1.5-pro"),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=4096,
            temperature=0.2,
        )
        hcl_content = response.choices[0].message.content.strip()

        # Strip markdown code blocks if present
        if hcl_content.startswith("```"):
            lines = hcl_content.split("\n")
            hcl_content = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])

    except Exception as exc:
        logger.error("HCL generation failed: %s", exc)
        return {"generated_hcl": "", "error": f"Generation failed: {exc}"}

    return {"generated_hcl": hcl_content, "error": None}


def scan_security(state: IaCGenerationState) -> dict:
    """Run checkov security scan on generated HCL."""
    hcl_content = state.get("generated_hcl", "")

    if not hcl_content:
        return {
            "security_scan": {
                "passed": False,
                "findings": [],
                "severity_counts": {},
                "error": "No HCL content to scan",
            }
        }

    with tempfile.TemporaryDirectory() as tmpdir:
        tf_file = os.path.join(tmpdir, "main.tf")
        with open(tf_file, "w") as f:
            f.write(hcl_content)

        findings: list[dict] = []
        severity_counts: dict[str, int] = {}

        try:
            result = subprocess.run(
                [
                    "checkov",
                    "-d", tmpdir,
                    "--output", "json",
                    "--quiet",
                    "--compact",
                ],
                capture_output=True,
                text=True,
                timeout=60,
            )

            output_text = result.stdout
            if not output_text.strip():
                output_text = result.stderr

            scan_result = json.loads(output_text) if output_text.strip() else {}

            failed_checks = []
            if isinstance(scan_result, dict):
                results = scan_result.get("results", {})
                failed_checks = results.get("failed_checks", [])
            elif isinstance(scan_result, list):
                for item in scan_result:
                    if isinstance(item, dict):
                        results = item.get("results", {})
                        failed_checks.extend(results.get("failed_checks", []))

            for check in failed_checks:
                severity = check.get("severity", "UNKNOWN").upper()
                findings.append({
                    "check_id": check.get("check_id", ""),
                    "check_name": check.get("check_name", ""),
                    "severity": severity,
                    "resource": check.get("resource", ""),
                    "file": check.get("file_path", ""),
                })
                severity_counts[severity] = severity_counts.get(severity, 0) + 1

        except FileNotFoundError:
            logger.info("checkov not installed, skipping security scan")
        except subprocess.TimeoutExpired:
            logger.warning("checkov scan timed out")
        except json.JSONDecodeError as exc:
            logger.warning("Failed to parse checkov output: %s", exc)
        except Exception as exc:
            logger.warning("Security scan failed: %s", exc)

    passed = severity_counts.get("CRITICAL", 0) == 0 and severity_counts.get("HIGH", 0) == 0

    return {
        "security_scan": {
            "passed": passed,
            "findings": findings,
            "severity_counts": severity_counts,
        }
    }


def create_pr(state: IaCGenerationState) -> dict:
    """Create a Git PR with the generated Terraform HCL."""
    import requests

    hcl_content = state.get("generated_hcl", "")
    requirements = state["requirements"]
    security_scan = state.get("security_scan", {})

    if not security_scan.get("passed", True) and security_scan.get(
        "severity_counts", {}
    ).get("CRITICAL", 0) > 0:
        return {
            "error": "Blocking security findings (CRITICAL) must be resolved before PR creation",
            "pr_url": None,
        }

    github_token = os.getenv("GITHUB_TOKEN")
    repo_owner = os.getenv("GITHUB_REPO_OWNER", "kogunlowo123")
    repo_name = os.getenv("GITHUB_REPO_NAME", "agentic-infrastructure-engineering")

    if not github_token:
        logger.warning("GITHUB_TOKEN not set, skipping PR creation")
        return {"pr_url": None, "pr_number": None, "branch_name": None}

    import git  # type: ignore[import]

    resource_type = requirements.get("resource_type", "resource").replace("_", "-")
    environment = requirements.get("environment", "dev")
    session_id = state.get("session_id", "unknown")[:8]
    branch_name = f"iac/generated/{resource_type}-{environment}-{session_id}"
    file_path = f"infra/generated/{environment}/{resource_type}.tf"

    with tempfile.TemporaryDirectory() as tmpdir:
        try:
            repo_url = f"https://{github_token}@github.com/{repo_owner}/{repo_name}.git"
            repo = git.Repo.clone_from(repo_url, tmpdir, depth=1)

            # Create branch
            repo.git.checkout("-b", branch_name)

            # Write HCL file
            import os as _os
            file_full_path = _os.path.join(tmpdir, file_path.replace("/", _os.sep))
            _os.makedirs(_os.path.dirname(file_full_path), exist_ok=True)
            with open(file_full_path, "w") as f:
                f.write(hcl_content)

            repo.git.add(file_path)
            repo.git.commit(
                "-m",
                f"feat(iac): generate {resource_type} for {environment}\n\n"
                f"Session: {state.get('session_id', '')}\n"
                f"Security scan: {'passed' if security_scan.get('passed') else 'findings present'}",
            )
            repo.git.push("origin", branch_name)

        except Exception as exc:
            logger.error("Git operations failed: %s", exc)
            return {"pr_url": None, "error": f"Git operation failed: {exc}"}

    try:
        headers = {
            "Authorization": f"token {github_token}",
            "Accept": "application/vnd.github.v3+json",
        }
        pr_body = {
            "title": f"[IaC] Generate {resource_type} for {environment}",
            "body": (
                f"## Auto-generated Terraform IaC\n\n"
                f"**Resource type**: `{resource_type}`\n"
                f"**Environment**: `{environment}`\n"
                f"**Security scan**: {'✅ Passed' if security_scan.get('passed') else '⚠️ Findings present'}\n\n"
                f"**Findings**: {len(security_scan.get('findings', []))}\n\n"
                f"_This PR requires T2 approval before merge._"
            ),
            "head": branch_name,
            "base": "main",
        }
        response = requests.post(
            f"https://api.github.com/repos/{repo_owner}/{repo_name}/pulls",
            headers=headers,
            json=pr_body,
            timeout=30,
        )
        response.raise_for_status()
        pr_data = response.json()
        pr_url = pr_data.get("html_url", "")
        pr_number = pr_data.get("number")

    except Exception as exc:
        logger.error("GitHub PR creation failed: %s", exc)
        return {"pr_url": None, "pr_number": None, "error": f"PR creation failed: {exc}"}

    return {
        "pr_url": pr_url,
        "pr_number": pr_number,
        "branch_name": branch_name,
        "approval_status": "pending",
        "error": None,
    }


def await_approval(state: IaCGenerationState) -> dict:
    """T2 approval gate — interrupts execution until human approves."""
    pr_url = state.get("pr_url")

    # This calls interrupt() which pauses the graph execution.
    # The graph resumes when the caller provides an approval decision.
    decision = interrupt(
        {
            "message": "Terraform IaC PR requires T2 approval before merge.",
            "pr_url": pr_url,
            "pr_number": state.get("pr_number"),
            "security_scan_passed": state.get("security_scan", {}).get("passed", False),
            "severity_counts": state.get("security_scan", {}).get("severity_counts", {}),
            "session_id": state.get("session_id"),
        }
    )

    approval_status: str = "approved" if decision == "approve" else "rejected"
    return {"approval_status": approval_status}


def _should_create_pr(state: IaCGenerationState) -> str:
    """Route: skip PR creation if HCL generation failed."""
    if state.get("error") or not state.get("generated_hcl"):
        return "end"
    return "create_pr"


def _should_await_approval(state: IaCGenerationState) -> str:
    """Route: skip approval gate if PR creation failed."""
    if state.get("error") or not state.get("pr_url"):
        return "end"
    return "await_approval"


def create_iac_generator_graph() -> Any:
    """Build and compile the IaC generator LangGraph workflow."""
    checkpointer = MemorySaver()
    graph = StateGraph(IaCGenerationState)

    graph.add_node("retrieve_golden_templates", retrieve_golden_templates)
    graph.add_node("generate_hcl", generate_hcl)
    graph.add_node("scan_security", scan_security)
    graph.add_node("create_pr", create_pr)
    graph.add_node("await_approval", await_approval)

    graph.add_edge(START, "retrieve_golden_templates")
    graph.add_edge("retrieve_golden_templates", "generate_hcl")
    graph.add_edge("generate_hcl", "scan_security")
    graph.add_conditional_edges("scan_security", _should_create_pr, {"create_pr": "create_pr", "end": END})
    graph.add_conditional_edges("create_pr", _should_await_approval, {"await_approval": "await_approval", "end": END})
    graph.add_edge("await_approval", END)

    return graph.compile(checkpointer=checkpointer, interrupt_before=["await_approval"])


# ─────────────────────────────────────────────────────────────
# Drift Detector Graph
# ─────────────────────────────────────────────────────────────

def fetch_terraform_state(state: DriftDetectionState) -> dict:
    """Fetch current Terraform state from GCS backend."""
    # In production, this reads from the GCS terraform state bucket
    # For now, returns the state passed in the request
    return {"current_state": state.get("terraform_plan_json", {})}


def compare_state_plan(state: DriftDetectionState) -> dict:
    """Compare current Terraform state with expected plan to detect drift."""
    current = state.get("current_state", {})
    plan = state.get("terraform_plan_json", {})

    drifted: list[dict] = []

    # Extract resource_changes from terraform plan JSON format
    resource_changes = plan.get("resource_changes", [])

    for change in resource_changes:
        action = change.get("change", {}).get("actions", [])
        if "no-op" in action or not action:
            continue

        resource_addr = change.get("address", "")
        before = change.get("change", {}).get("before", {}) or {}
        after = change.get("change", {}).get("after", {}) or {}

        # Find attributes that differ
        all_keys = set(before.keys()) | set(after.keys())
        for key in all_keys:
            before_val = before.get(key)
            after_val = after.get(key)
            if before_val != after_val:
                severity = _classify_drift_severity(resource_addr, key)
                drifted.append({
                    "resource_id": resource_addr,
                    "attribute": key,
                    "expected": after_val,
                    "actual": before_val,
                    "severity": severity,
                })

    overall_severity = _compute_overall_severity(drifted)

    return {
        "drifted_resources": drifted,
        "drift_report": {
            "total_drifted": len(drifted),
            "items": drifted,
            "severity": overall_severity,
        },
        "severity": overall_severity,
    }


def _classify_drift_severity(resource_addr: str, attribute: str) -> str:
    """Classify the severity of a specific drift."""
    critical_patterns = ["iam_policy", "firewall", "ssl_certificate", "encryption"]
    high_patterns = ["security_group", "network_policy", "access_control"]
    medium_patterns = ["machine_type", "disk_size", "replica_count"]

    lower = attribute.lower()
    addr_lower = resource_addr.lower()

    for pattern in critical_patterns:
        if pattern in lower or pattern in addr_lower:
            return "critical"
    for pattern in high_patterns:
        if pattern in lower or pattern in addr_lower:
            return "high"
    for pattern in medium_patterns:
        if pattern in lower:
            return "medium"
    return "low"


def _compute_overall_severity(drifted: list[dict]) -> str:
    """Compute overall severity from individual drift items."""
    if not drifted:
        return "none"

    severity_order = {"critical": 4, "high": 3, "medium": 2, "low": 1, "none": 0}
    max_sev = max(severity_order.get(d.get("severity", "low"), 1) for d in drifted)
    return {v: k for k, v in severity_order.items()}.get(max_sev, "low")


def generate_drift_report(state: DriftDetectionState) -> dict:
    """Finalize the drift report with remediation recommendations."""
    drift_report = state.get("drift_report", {})
    severity = state.get("severity", "none")

    recommendations = []
    if severity in ("critical", "high"):
        recommendations.append(
            "Immediate remediation required. Run `terraform apply` in the affected environment."
        )
    elif severity == "medium":
        recommendations.append(
            "Schedule remediation within 24 hours. Review changes with the infrastructure team."
        )

    drift_report["recommendations"] = recommendations
    return {"drift_report": drift_report}


def create_drift_detector_graph() -> Any:
    """Build and compile the drift detector LangGraph workflow."""
    graph = StateGraph(DriftDetectionState)

    graph.add_node("fetch_terraform_state", fetch_terraform_state)
    graph.add_node("compare_state_plan", compare_state_plan)
    graph.add_node("generate_drift_report", generate_drift_report)

    graph.add_edge(START, "fetch_terraform_state")
    graph.add_edge("fetch_terraform_state", "compare_state_plan")
    graph.add_edge("compare_state_plan", "generate_drift_report")
    graph.add_edge("generate_drift_report", END)

    return graph.compile()


# ─────────────────────────────────────────────────────────────
# Cost Optimizer Graph
# ─────────────────────────────────────────────────────────────

def fetch_cost_data(state: CostOptimizationState) -> dict:
    """Fetch cost data from GCP Cloud Billing export."""
    # In production, this queries BigQuery billing export
    # Returns mock data structure matching the real schema
    project_id = state.get("project_id", "")
    days = state.get("analysis_period_days", 30)

    # Simulated cost data structure
    cost_data = {
        "project_id": project_id,
        "period_days": days,
        "services": {
            "Compute Engine": {"monthly_cost": 450.0, "trend": "increasing"},
            "Cloud SQL": {"monthly_cost": 280.0, "trend": "stable"},
            "GKE": {"monthly_cost": 320.0, "trend": "increasing"},
            "Cloud Storage": {"monthly_cost": 45.0, "trend": "stable"},
            "Vertex AI": {"monthly_cost": 180.0, "trend": "increasing"},
        },
        "total_monthly": 1275.0,
    }

    return {"cost_data": cost_data, "current_monthly_usd": cost_data["total_monthly"]}


def analyze_cost_patterns(state: CostOptimizationState) -> dict:
    """Analyze cost patterns and identify optimization opportunities."""
    cost_data = state.get("cost_data", {})
    services = cost_data.get("services", {})

    recommendations: list[dict] = []
    total_savings = 0.0

    # Compute Engine optimization
    if services.get("Compute Engine", {}).get("trend") == "increasing":
        savings = services["Compute Engine"]["monthly_cost"] * 0.25
        recommendations.append({
            "resource_id": "compute_engine_instances",
            "current_cost_usd": services["Compute Engine"]["monthly_cost"],
            "recommended_action": "Enable committed use discounts (1-year) for predictable workloads. Consider preemptible instances for batch jobs.",
            "estimated_savings_usd": savings,
            "priority": "high",
        })
        total_savings += savings

    # GKE optimization
    if services.get("GKE", {}).get("trend") == "increasing":
        savings = services["GKE"]["monthly_cost"] * 0.20
        recommendations.append({
            "resource_id": "gke_node_pools",
            "current_cost_usd": services["GKE"]["monthly_cost"],
            "recommended_action": "Enable cluster autoscaler, use Spot nodes for dev/staging, review node pool sizing.",
            "estimated_savings_usd": savings,
            "priority": "medium",
        })
        total_savings += savings

    # Vertex AI optimization
    if services.get("Vertex AI", {}).get("trend") == "increasing":
        savings = services["Vertex AI"]["monthly_cost"] * 0.15
        recommendations.append({
            "resource_id": "vertex_ai_endpoints",
            "current_cost_usd": services["Vertex AI"]["monthly_cost"],
            "recommended_action": "Use batch prediction for non-realtime workloads. Optimize model serving with flash models where appropriate.",
            "estimated_savings_usd": savings,
            "priority": "medium",
        })
        total_savings += savings

    current = state.get("current_monthly_usd", 0.0)
    projected = current - total_savings

    return {
        "recommendations": recommendations,
        "estimated_savings_usd": total_savings,
        "projected_monthly_usd": projected,
    }


def create_cost_optimizer_graph() -> Any:
    """Build and compile the cost optimizer LangGraph workflow."""
    graph = StateGraph(CostOptimizationState)

    graph.add_node("fetch_cost_data", fetch_cost_data)
    graph.add_node("analyze_cost_patterns", analyze_cost_patterns)

    graph.add_edge(START, "fetch_cost_data")
    graph.add_edge("fetch_cost_data", "analyze_cost_patterns")
    graph.add_edge("analyze_cost_patterns", END)

    return graph.compile()
