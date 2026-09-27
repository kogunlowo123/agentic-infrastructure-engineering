# ADR 0001: IaC Generation Approach

## Status

Accepted

## Date

2024-01-01

## Context

The platform must generate production-ready Terraform HCL for GCP resources from
structured requirements. Key constraints:

- Generated HCL must pass checkov security scans before PR creation
- A T2 human-in-the-loop approval gate is required before merge
- Golden template retrieval (RAG) must reduce hallucination rate
- The system must be auditable: every generation logged with session_id

## Decision

Use a LangGraph `StateGraph` for the IaC generation workflow with the following
node sequence:

1. `retrieve_golden_templates` — Hybrid RAG retrieval (pgvector + OpenSearch BM25)
   returns top-5 golden HCL examples as context
2. `generate_hcl` — LiteLLM call to `vertex_ai/gemini-1.5-pro` with retrieved
   context and structured prompt; output is raw HCL string
3. `scan_security` — checkov subprocess scan in temporary directory; findings
   parsed and attached to state
4. `create_pr` — GitPython creates branch, commits HCL, opens GitHub PR;
   PR URL and number stored in state
5. `await_approval` — LangGraph `interrupt()` pauses graph; T2 approver calls
   `POST /api/v1/iac/approvals/{session_id}` to resume with approve/reject decision

The `interrupt()` approach was chosen over polling because:
- The graph is paused at the exact `await_approval` node — no busy-wait
- State is persisted by `MemorySaver` across the interruption
- Resume is a single `graph.invoke(None, config, ...)` call with the decision

## Alternatives Considered

### Separate approval microservice
Rejected: adds network hop, state duplication, deployment complexity.

### Async task queue (Celery/Cloud Tasks)
Rejected: harder to express sequential graph logic; LangGraph's interrupt is
purpose-built for this pattern.

### Immediate merge without approval gate
Rejected: violates the T2 requirement for IaC changes. Terraform apply on prod
without human review is an unacceptable risk.

## Consequences

- T2 approval is blocking: the session occupies a worker slot until the approver
  acts (mitigated by TTL and max-sessions-per-tenant limits)
- checkov subprocess adds ~2s per generation; acceptable for a 202 async flow
- HCL quality depends on retrieval quality — Recall@5 ≥ 0.70 threshold enforced in CI
