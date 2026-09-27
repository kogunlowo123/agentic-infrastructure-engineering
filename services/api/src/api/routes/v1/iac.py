"""IaC generation routes."""

from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, status

from ...schemas.iac import (
    IaCGenerationRequest,
    IaCGenerationResult,
    IaCPRStatus,
    SecurityFinding,
    SecurityScanResult,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/iac", tags=["IaC"])

AGENT_RUNTIME_URL = os.getenv("AGENT_RUNTIME_URL", "http://agent-runtime:8081")


async def get_agent_client() -> httpx.AsyncClient:
    """Dependency: returns an async HTTP client for agent-runtime."""
    async with httpx.AsyncClient(
        base_url=AGENT_RUNTIME_URL,
        timeout=300.0,
    ) as client:
        yield client


@router.post(
    "/generate",
    response_model=IaCGenerationResult,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Generate Terraform IaC from requirements",
    description=(
        "Invokes the iac-generator LangGraph agent to produce Terraform HCL "
        "from natural language requirements, runs a security scan, and creates a PR. "
        "T2 approval gate: the PR is created but merge requires human approval."
    ),
)
async def generate_iac(
    request: IaCGenerationRequest,
    client: httpx.AsyncClient = Depends(get_agent_client),
    x_tenant_id: str = Header(default="default"),
    x_trace_id: str = Header(default=""),
) -> IaCGenerationResult:
    """Generate Terraform IaC from requirements."""
    session_id = str(uuid.uuid4())
    trace_id = x_trace_id or str(uuid.uuid4())

    payload: dict[str, Any] = {
        "task_type": "iac_generation",
        "session_id": session_id,
        "trace_id": trace_id,
        "tenant_id": x_tenant_id,
        "input": {
            "requirements": {
                "resource_type": request.resource_type,
                "cloud": request.cloud,
                "environment": request.environment,
                "config": request.config,
                "project_id": request.project_id,
            },
            "retrieved_templates": [],
            "generated_hcl": "",
            "security_scan": {},
            "pr_url": None,
            "pr_number": None,
            "branch_name": None,
            "approval_status": "pending",
            "error": None,
            "retry_count": 0,
            "session_id": session_id,
            "trace_id": trace_id,
            "tenant_id": x_tenant_id,
        },
    }

    # Check idempotency
    if request.idempotency_key:
        try:
            idempotency_response = await client.get(
                f"/idempotency/{request.idempotency_key}"
            )
            if idempotency_response.status_code == 200:
                cached = idempotency_response.json()
                if cached:
                    return IaCGenerationResult(**cached)
        except Exception:
            pass

    try:
        response = await client.post("/run", json=payload)
        response.raise_for_status()
        result_data = response.json()
    except httpx.HTTPStatusError as exc:
        logger.error("Agent runtime error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Agent runtime error: {exc.response.status_code}",
        ) from exc
    except httpx.RequestError as exc:
        logger.error("Agent runtime unreachable: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Agent runtime service unavailable",
        ) from exc

    # Extract results from agent state
    agent_state = result_data.get("state", {})
    security_data = agent_state.get("security_scan", {})

    findings = [
        SecurityFinding(
            check_id=f.get("check_id", ""),
            severity=f.get("severity", "UNKNOWN"),
            resource=f.get("resource", ""),
            message=f.get("check_name", ""),
            check_name=f.get("check_name", ""),
        )
        for f in security_data.get("findings", [])
    ]

    security_result = SecurityScanResult(
        passed=security_data.get("passed", True),
        findings=findings,
        severity_counts=security_data.get("severity_counts", {}),
    )

    hcl_content = agent_state.get("generated_hcl", "")
    hcl_preview = hcl_content[:2000] if hcl_content else ""

    return IaCGenerationResult(
        pr_url=agent_state.get("pr_url"),
        hcl_preview=hcl_preview,
        security_scan_result=security_result,
        session_id=session_id,
        pr_ready=security_data.get("passed", False),
        approval_status=agent_state.get("approval_status", "pending"),
    )


@router.get(
    "/{pr_id}/status",
    response_model=IaCPRStatus,
    summary="Get IaC PR status",
)
async def get_pr_status(
    pr_id: str,
    client: httpx.AsyncClient = Depends(get_agent_client),
    x_tenant_id: str = Header(default="default"),
) -> IaCPRStatus:
    """Get the status of an IaC pull request by session/PR ID."""
    try:
        response = await client.get(f"/sessions/{pr_id}")
        response.raise_for_status()
        session_data = response.json()
    except httpx.HTTPStatusError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"PR/session {pr_id!r} not found",
        )
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Agent runtime service unavailable",
        ) from exc

    state = session_data.get("state_json", {})
    approval_status = state.get("approval_status", "pending")

    pr_status: IaCPRStatus = IaCPRStatus(
        pr_id=pr_id,
        status="pending_approval" if approval_status == "pending" else "open",
        pr_url=state.get("pr_url"),
        approval_status=approval_status,
        created_at=datetime.now(tz=timezone.utc),
        session_id=pr_id,
    )
    return pr_status
