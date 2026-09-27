# STRIDE Threat Model: Agentic Infrastructure Engineering Platform

## Scope

This threat model covers the Agentic Infrastructure Engineering platform components:
- API Gateway (FastAPI)
- Agent Runtime (LangGraph orchestrator)
- RAG Core (vector retrieval)
- Platform Gateway (LLM routing)
- Identity Broker
- GCP Infrastructure (GKE, Cloud SQL, GCS, Pub/Sub)

## Assets

| Asset | Sensitivity | Owner |
|-------|-------------|-------|
| Terraform state files | Critical | Platform |
| LLM API keys / credentials | Critical | Platform |
| Agent session tokens | High | Identity Broker |
| Generated HCL | High | Agent Runtime |
| Vector embeddings | Medium | RAG Core |
| Cost/usage data | Medium | Platform |

## STRIDE Analysis

### Spoofing

| Threat | Mitigation |
|--------|-----------|
| Attacker impersonates legitimate tenant | JWT validation with HS256; tenant_id claim enforced on every request |
| Malicious agent forges identity token | HMAC-signed credentials from Identity Broker; short TTL (1h) |
| Prompt injection to override agent identity | InputScreener blocks injection patterns before LLM call |

### Tampering

| Threat | Mitigation |
|--------|-----------|
| Unauthorized Terraform state modification | GCS bucket CMEK + IAM; Sigma rule `unauthorized-iac-change` |
| Modified HCL before PR merge | checkov scan on generated HCL; T2 approval gate |
| Database record manipulation | Cloud SQL private IP + IAM auth; no public endpoint |

### Repudiation

| Threat | Mitigation |
|--------|-----------|
| Agent denies generating malicious HCL | Audit log in PostgreSQL with session_id, tenant_id, timestamp |
| Approver denies T2 decision | Approval requests table with `decided_by`, `decided_at` |
| Cost charges disputed | Budget enforcer records per-tenant token + USD spend |

### Information Disclosure

| Threat | Mitigation |
|--------|-----------|
| LLM response leaks secrets from context | PII scrub processor in OTel collector; audit log excludes bodies |
| Vector embeddings expose sensitive code | ACL filter in retrieval pipeline; tenant isolation |
| Cost data exposed cross-tenant | OPA policy enforces tenant_id match; API middleware |

### Denial of Service

| Threat | Mitigation |
|--------|-----------|
| Token flooding exhausts LLM quota | Budget enforcer hard cutoff; rate limit middleware (30 RPM/tenant) |
| Large HCL generation blocks agent workers | Token budget (max 8192 output tokens per request) |
| Session storm fills PostgreSQL | Max 10 sessions per tenant; TTL-based eviction |

### Elevation of Privilege

| Threat | Mitigation |
|--------|-----------|
| T1 agent attempts T2 operation | OPA policy checks `input.user.tier`; scope validation in Identity Broker |
| Container escapes to host | Kyverno `disallow-privileged`; GKE Autopilot node isolation |
| Workload Identity misuse | Least-privilege GSA; scope limited to specific GCS buckets and Pub/Sub topics |

## Residual Risks

1. Vertex AI model hallucination producing syntactically valid but semantically dangerous HCL — mitigated by checkov but not eliminated
2. Supply chain compromise of Python dependencies — mitigated by Dependabot and SBOM but not zero-risk
3. GCP service account key leakage — mitigated by Workload Identity (no key files) but human error possible

## Review Schedule

This threat model is reviewed quarterly or after any significant architecture change.
