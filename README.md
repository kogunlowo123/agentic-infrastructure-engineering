# Agentic Infrastructure Engineering

[![CI](https://github.com/kogunlowo123/agentic-infrastructure-engineering/actions/workflows/ci.yml/badge.svg)](https://github.com/kogunlowo123/agentic-infrastructure-engineering/actions/workflows/ci.yml)
[![Security](https://github.com/kogunlowo123/agentic-infrastructure-engineering/actions/workflows/security.yml/badge.svg)](https://github.com/kogunlowo123/agentic-infrastructure-engineering/actions/workflows/security.yml)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![Terraform 1.8+](https://img.shields.io/badge/terraform-1.8+-purple.svg)](https://www.terraform.io/)

An enterprise-grade AI platform for **Agentic Infrastructure Engineering** — autonomous AI agents that generate Terraform Infrastructure as Code (IaC), detect configuration drift, optimize cloud costs, and manage the full infrastructure lifecycle on Google Cloud Platform.

---

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Agents](#agents)
- [Quickstart](#quickstart)
- [API Reference](#api-reference)
- [Deployment to GCP GKE](#deployment-to-gcp-gke)
- [Configuration](#configuration)
- [Contributing](#contributing)
- [Security](#security)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    API Gateway (FastAPI)                         │
│              services/api  ·  Port 8000                         │
└──────────────────────┬──────────────────────────────────────────┘
                       │ gRPC / REST
          ┌────────────┼────────────┐
          ▼            ▼            ▼
   ┌─────────────┐ ┌──────────┐ ┌───────────────┐
   │ IaC         │ │ Drift    │ │ Cost          │
   │ Generator   │ │ Detector │ │ Optimizer     │
   │ Agent       │ │ Agent    │ │ Agent         │
   └──────┬──────┘ └────┬─────┘ └───────┬───────┘
          │             │               │
          └─────────────┴───────────────┘
                        │
              ┌─────────▼──────────┐
              │   Agent Runtime    │
              │ (LangGraph 0.2+)   │
              │ services/agent-    │
              │ runtime            │
              └─────────┬──────────┘
                        │
          ┌─────────────┼─────────────┐
          ▼             ▼             ▼
   ┌────────────┐ ┌──────────┐ ┌───────────┐
   │ RAG Core   │ │ Postgres │ │  Redis    │
   │ (pgvector) │ │ (state)  │ │ (cache)   │
   └────────────┘ └──────────┘ └───────────┘
          │
   ┌──────▼───────┐
   │  OpenSearch  │
   │  (vectors)   │
   └──────────────┘

   GCP Services:
   ├── Vertex AI (LLM inference via LiteLLM)
   ├── GKE (container orchestration)
   ├── Cloud SQL (managed Postgres)
   ├── Cloud Memorystore (Redis)
   ├── Secret Manager (credentials)
   ├── Artifact Registry (container images)
   └── Cloud Monitoring / Trace (observability)
```

### Component Description

| Component | Technology | Purpose |
|-----------|-----------|---------|
| `services/api` | FastAPI 0.111+ | REST/WebSocket gateway, auth, routing |
| `services/agent-runtime` | LangGraph 0.2+, LiteLLM 1.40+ | Agent execution, tool orchestration |
| `services/rag-core` | pgvector, OpenSearch | Terraform doc embedding & retrieval |
| `infra/gcp` | Terraform 1.8+ | GCP infrastructure definitions |

---

## Agents

### IaC Generator (`iac-generator`)

Generates production-grade Terraform modules from natural language or structured intent. Uses RAG over Terraform provider documentation, existing module libraries, and organizational policy constraints.

**Capabilities:**
- Generates complete Terraform root modules for common GCP patterns (GKE, Cloud SQL, VPC, IAM)
- Applies organizational policy guardrails (resource labeling, network constraints, KMS encryption)
- Produces `checkov`-clean IaC with security best practices baked in
- Outputs module files with `variables.tf`, `outputs.tf`, `main.tf`, and `README.md`
- Integrates with GitHub to open PRs directly to target repositories

**Workflow:**
```
User Intent → Intent Parser → RAG Retrieval → Template Selection
    → Terraform Generation → Policy Validation → Checkov Scan
    → GitHub PR Creation → Human Review → Apply
```

---

### Drift Detector (`drift-detector`)

Continuously compares desired infrastructure state (Terraform state files) against live GCP resource configurations. Alerts on unauthorized changes and generates remediation plans.

**Capabilities:**
- Polls GCP APIs for resource configuration snapshots
- Diffs against last-known Terraform state
- Classifies drift severity (informational / warning / critical)
- Generates `terraform plan` remediation snippets
- Sends structured alerts to PagerDuty, Slack, or GitHub Issues
- Supports scheduled runs and webhook-triggered scans

**Workflow:**
```
Trigger (schedule/webhook) → State Fetch → GCP API Scan
    → Diff Engine → Severity Classification → Alert Routing
    → Remediation Plan Generation → Ticket/PR Creation
```

---

### Cost Optimizer (`cost-optimizer`)

Analyzes GCP billing data, Terraform configurations, and usage metrics to identify cost optimization opportunities and generate actionable recommendations with estimated savings.

**Capabilities:**
- Ingests GCP Cloud Billing exports (BigQuery)
- Identifies idle, oversized, and underutilized resources
- Recommends committed use discounts (CUDs) and sustained use discounts
- Generates optimized Terraform diffs (e.g., machine type downsizing)
- Tracks historical optimization actions and realized savings
- Supports configurable alert thresholds (`COST_ALERT_THRESHOLD_USD`)

**Workflow:**
```
Billing Export → Usage Analysis → Optimization Identification
    → Savings Estimation → Terraform Diff Generation
    → Recommendation Report → Optional Auto-PR
```

---

## Quickstart

### Prerequisites

- Python 3.12+
- [uv](https://github.com/astral-sh/uv) package manager
- Docker & Docker Compose
- Terraform 1.8+
- GCP project with billing enabled
- `gcloud` CLI authenticated

### 1. Clone and configure

```bash
git clone https://github.com/kogunlowo123/agentic-infrastructure-engineering.git
cd agentic-infrastructure-engineering

# Copy and edit environment configuration
cp .env.example .env
# Edit .env with your GCP project ID, credentials, etc.
```

### 2. Install dependencies

```bash
# Install uv if not present
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install all service dependencies
make install
```

### 3. Start local development stack

```bash
# Copy the docker-compose override example
cp docker-compose.override.example.yml docker-compose.override.yml

# Start all services
make dev
# or
docker compose up -d
```

### 4. Verify the stack is running

```bash
# Check service health
curl http://localhost:8000/health

# View API docs
open http://localhost:8000/docs
```

### 5. Run your first IaC generation

```bash
curl -X POST http://localhost:8000/v1/agents/iac-generator/run \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -d '{
    "intent": "Create a GKE cluster with 3 node pools for a production workload",
    "constraints": {
      "region": "us-central1",
      "environment": "production",
      "labels": {"team": "platform", "cost-center": "eng"}
    }
  }'
```

---

## API Reference

All endpoints require JWT authentication. Obtain a token via `POST /v1/auth/token`.

### Authentication

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/v1/auth/token` | Exchange API key for JWT |
| `POST` | `/v1/auth/refresh` | Refresh an expiring JWT |

### IaC Generator

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/v1/agents/iac-generator/run` | Run IaC generation synchronously |
| `POST` | `/v1/agents/iac-generator/run-async` | Start async IaC generation job |
| `GET` | `/v1/agents/iac-generator/jobs/{job_id}` | Get job status and results |
| `GET` | `/v1/agents/iac-generator/templates` | List available IaC templates |

### Drift Detector

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/v1/agents/drift-detector/scan` | Trigger a drift scan |
| `GET` | `/v1/agents/drift-detector/scans/{scan_id}` | Get scan results |
| `GET` | `/v1/agents/drift-detector/drift` | List current drift findings |
| `POST` | `/v1/agents/drift-detector/drift/{drift_id}/remediate` | Generate remediation plan |

### Cost Optimizer

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/v1/agents/cost-optimizer/analyze` | Run cost analysis |
| `GET` | `/v1/agents/cost-optimizer/recommendations` | List optimization recommendations |
| `GET` | `/v1/agents/cost-optimizer/recommendations/{rec_id}` | Get recommendation details |
| `POST` | `/v1/agents/cost-optimizer/recommendations/{rec_id}/apply` | Apply recommendation |

### Health & Observability

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Service health check |
| `GET` | `/ready` | Kubernetes readiness probe |
| `GET` | `/metrics` | Prometheus metrics endpoint |

---

## Deployment to GCP GKE

### Prerequisites

- GCP project with required APIs enabled
- `gcloud` authenticated with `roles/owner` or equivalent IAM
- Workload Identity Federation configured for GitHub Actions

### 1. Provision infrastructure

```bash
cd infra/gcp/environments/production

# Initialize and apply core infrastructure
terraform init
terraform plan -out=tfplan
terraform apply tfplan
```

### 2. Configure Workload Identity Federation

```bash
# Set up WIF for GitHub Actions CI/CD
cd infra/gcp/modules/workload-identity-federation
terraform init && terraform apply \
  -var="github_org=kogunlowo123" \
  -var="github_repo=agentic-infrastructure-engineering"
```

### 3. Build and push container images

```bash
# Authenticate to Artifact Registry
gcloud auth configure-docker us-central1-docker.pkg.dev

# Build and push all service images
make docker-build docker-push \
  GCP_PROJECT_ID=your-project-id \
  GCP_REGION=us-central1
```

### 4. Deploy to GKE

```bash
# Get GKE credentials
gcloud container clusters get-credentials agentic-infra-prod \
  --region us-central1 \
  --project your-project-id

# Apply Kubernetes manifests
kubectl apply -k infra/kubernetes/overlays/production
```

### 5. Configure DNS and TLS

```bash
# External IP is provisioned via Cloud Load Balancer
kubectl get service -n agentic-infra ingress-nginx-controller

# Configure your DNS to point to the external IP
# TLS certificates are managed via cert-manager + Let's Encrypt
```

---

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GCP_PROJECT_ID` | Yes | — | GCP project ID for all resources |
| `GCP_REGION` | Yes | `us-central1` | Primary GCP region |
| `VERTEX_AI_LOCATION` | Yes | `us-central1` | Vertex AI API endpoint location |
| `DATABASE_URL` | Yes | — | PostgreSQL connection string (with pgvector) |
| `OPENSEARCH_URL` | Yes | — | OpenSearch cluster URL for vector search |
| `GITHUB_TOKEN` | Yes | — | GitHub PAT or App token for PR creation |
| `GITHUB_REPO_OWNER` | Yes | — | Target GitHub organization or user |
| `GITHUB_REPO_NAME` | Yes | — | Target GitHub repository name |
| `JWT_SECRET_KEY` | Yes | — | Secret key for JWT signing (min 32 chars) |
| `JWT_ALGORITHM` | No | `HS256` | JWT signing algorithm |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | No | — | OpenTelemetry collector endpoint |
| `CHECKOV_SKIP_CHECKS` | No | — | Comma-separated Checkov check IDs to skip |
| `RAG_EMBEDDING_MODEL` | No | `textembedding-gecko@003` | Vertex AI embedding model |
| `RAG_CHUNK_SIZE` | No | `1024` | Token chunk size for document splitting |
| `RAG_CHUNK_OVERLAP` | No | `128` | Token overlap between chunks |
| `COST_ALERT_THRESHOLD_USD` | No | `1000.0` | Monthly cost threshold for alerts |
| `LOG_LEVEL` | No | `INFO` | Application log level |
| `ENVIRONMENT` | No | `development` | Deployment environment name |

---

## Project Structure

```
agentic-infrastructure-engineering/
├── services/
│   ├── api/                    # FastAPI gateway service
│   │   ├── src/api/
│   │   │   ├── routers/        # Route handlers per agent
│   │   │   ├── middleware/     # Auth, tracing, rate limiting
│   │   │   ├── models/         # Pydantic request/response models
│   │   │   └── main.py
│   │   ├── tests/
│   │   └── pyproject.toml
│   ├── agent-runtime/          # LangGraph agent execution service
│   │   ├── src/agent_runtime/
│   │   │   ├── agents/         # iac_generator, drift_detector, cost_optimizer
│   │   │   ├── tools/          # GCP API tools, GitHub tools, Terraform tools
│   │   │   ├── graphs/         # LangGraph workflow definitions
│   │   │   └── state/          # Agent state schemas
│   │   ├── tests/
│   │   └── pyproject.toml
│   └── rag-core/               # RAG retrieval service
│       ├── src/rag_core/
│       │   ├── embedders/      # Vertex AI embedding clients
│       │   ├── retrievers/     # pgvector + OpenSearch retrievers
│       │   ├── chunkers/       # Document chunking strategies
│       │   └── indexers/       # Terraform doc indexing pipelines
│       ├── tests/
│       └── pyproject.toml
├── infra/
│   ├── gcp/                    # Terraform for GCP infrastructure
│   │   ├── modules/            # Reusable Terraform modules
│   │   └── environments/       # dev / staging / production
│   └── kubernetes/             # Kubernetes manifests (Kustomize)
│       ├── base/
│       └── overlays/
├── .github/
│   ├── actions/                # Reusable composite actions
│   └── workflows/              # CI/CD workflows
├── docs/                       # Extended documentation
└── scripts/                    # Operational scripts
```

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full contributing guide.

## Security

See [SECURITY.md](SECURITY.md) for the security policy and vulnerability reporting instructions.

## License

Copyright 2024 Agentic Infrastructure Engineering Contributors

Licensed under the [Apache License, Version 2.0](LICENSE).
