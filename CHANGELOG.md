# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added
- Nothing yet.

---

## [0.1.0] — 2024-01-01

### Added

#### Platform Core
- Initial project structure with three microservices: `services/api`, `services/agent-runtime`, `services/rag-core`
- FastAPI 0.111 API gateway with JWT authentication, OpenAPI documentation, and health/readiness endpoints
- LangGraph 0.2 agent runtime supporting stateful multi-step agent execution
- LiteLLM 1.40 integration for LLM routing to Vertex AI (Gemini) as primary provider
- Structured logging with `structlog` and OpenTelemetry trace propagation
- PostgreSQL with `pgvector` extension for vector storage and retrieval
- OpenSearch integration for hybrid keyword + vector search
- Redis integration for agent state caching and distributed locks

#### IaC Generator Agent
- Natural language to Terraform module generation using Vertex AI Gemini models
- RAG pipeline over Terraform provider documentation for GCP (compute, container, sql, storage, iam)
- Organizational policy enforcement: resource labeling, network constraints, KMS encryption defaults
- Automated `checkov` security scan on generated Terraform before output
- GitHub integration for automated PR creation with generated modules
- Async job execution with status polling via `GET /v1/agents/iac-generator/jobs/{job_id}`
- Template library for common GCP patterns: GKE cluster, Cloud SQL, VPC, GCS, IAM binding

#### Drift Detector Agent
- Periodic and on-demand drift scanning against Terraform state files stored in GCS
- GCP API polling for resource configuration snapshots (Compute Engine, GKE, Cloud SQL, GCS, IAM)
- Drift classification by severity: informational, warning, critical
- Automated remediation plan generation (`terraform plan` snippets for detected drift)
- Alert routing to Slack webhooks and GitHub Issues
- Configurable scan schedules via environment variable

#### Cost Optimizer Agent
- GCP Cloud Billing export ingestion from BigQuery
- Idle resource detection: stopped VMs, empty GCS buckets, unattached persistent disks
- Right-sizing recommendations for GCE instances based on CPU/memory utilization metrics
- Committed use discount (CUD) analysis and purchase recommendations
- Cost alert notifications when monthly spend exceeds `COST_ALERT_THRESHOLD_USD`
- Terraform diff generation for approved optimization recommendations
- Historical recommendation tracking and realized savings reporting

#### Infrastructure (Terraform)
- GKE Autopilot cluster module with Workload Identity and Binary Authorization
- Cloud SQL PostgreSQL module with pgvector extension, private IP, and automated backups
- VPC module with private subnets, Cloud NAT, and VPC Service Controls
- GCS bucket module with versioning, uniform ACL, and audit logging
- Secret Manager module for secure credential storage
- Artifact Registry repository module for container images
- Workload Identity Federation module for keyless GitHub Actions authentication
- Environment-specific configurations: `dev`, `staging`, `production`

#### CI/CD
- GitHub Actions CI workflow: lint, typecheck, unit tests, integration tests on Python 3.12
- Terraform workflow: `fmt`/`validate`/`plan` on PR, `apply` on push to `main` with manual approval for production
- Security workflow: Checkov, Trivy, Bandit, OWASP dependency check
- Release workflow: semantic version tagging, Docker image build/push, GKE deployment, GitHub Release creation

#### Developer Experience
- `uv`-based dependency management with lock files for reproducible builds
- `Makefile` with targets for all common development tasks
- `docker-compose.yml` with all services for local development
- Pre-commit hooks: `ruff`, `black`, `mypy`, `terraform fmt`, `checkov`
- `.editorconfig` for consistent IDE formatting
- Comprehensive `.gitignore` and `.dockerignore`
- Dependabot configuration for automated dependency updates
- GitHub issue templates: bug report, agent feature request, security finding
- PR template with IaC review and security checklists
- Composite GitHub Actions: `setup-python`, `setup-terraform`, `docker-build-push`

### Security
- JWT-based API authentication with configurable signing algorithm
- Secrets management via GCP Secret Manager (no secrets in environment variables in production)
- Container images run as non-root user with read-only filesystem
- All generated Terraform passes `checkov` with zero HIGH/CRITICAL findings by default
- Automated dependency vulnerability scanning in CI
- Trivy container image scanning on every build

---

[Unreleased]: https://github.com/kogunlowo123/agentic-infrastructure-engineering/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/kogunlowo123/agentic-infrastructure-engineering/releases/tag/v0.1.0
