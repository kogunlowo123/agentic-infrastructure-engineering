# Security Policy

## Overview

The Agentic Infrastructure Engineering project takes security seriously. This document describes our security policy, supported versions, and procedures for reporting vulnerabilities.

Because this platform operates on live cloud infrastructure and can generate and apply Terraform IaC, security vulnerabilities can have significant real-world impact. We are committed to addressing reports promptly and responsibly.

---

## Supported Versions

The following versions currently receive security updates:

| Version | Supported | End of Support |
|---------|-----------|----------------|
| 0.1.x (current) | ✅ Active | TBD |
| < 0.1.0 | ❌ Not supported | — |

We follow semantic versioning. Security patches are backported to the current minor release series only. Users are strongly encouraged to stay on the latest patch release.

---

## Reporting a Vulnerability

**Do not open a public GitHub issue for security vulnerabilities.**

Public disclosure of a security vulnerability before a fix is available can put users and their cloud infrastructure at risk.

### Private Disclosure

Please report security vulnerabilities via email to:

**kogunlowo@gmail.com**

Use the subject line: `[SECURITY] Agentic Infrastructure Engineering — <brief description>`

If the vulnerability is sensitive, please encrypt your message using our PGP key (see below).

### What to Include

Please include as much of the following as possible to help us triage and reproduce the issue:

1. **Affected component(s)**: e.g., `services/api`, `services/agent-runtime`, `infra/gcp`
2. **Affected version(s)**: Exact version or commit hash
3. **Vulnerability type**: e.g., authentication bypass, injection, privilege escalation, secret exposure
4. **Severity assessment**: Your estimate of CVSS score or impact level (Critical / High / Medium / Low)
5. **Description**: A clear description of the vulnerability
6. **Reproduction steps**: Step-by-step instructions to reproduce the issue
7. **Proof of concept**: Code, screenshots, or logs that demonstrate the issue (redact actual secrets)
8. **Suggested fix**: If you have one (optional but appreciated)
9. **Affected infrastructure**: Whether you tested this against real GCP infrastructure

### Scope

The following are **in scope** for security reports:

- Authentication and authorization flaws in the API service
- Injection vulnerabilities (SQL, command, Terraform code injection)
- Secrets exposure (environment variables, GCP credentials, GitHub tokens)
- Terraform state file exposure
- Agent privilege escalation or tool misuse
- RAG poisoning or prompt injection attacks affecting generated IaC
- Insecure defaults in generated Terraform code (e.g., public buckets, open firewall rules)
- Container image vulnerabilities in published images
- Dependency vulnerabilities with known exploits

The following are **out of scope**:

- Vulnerabilities in infrastructure you have deployed yourself (not our published images/modules)
- Issues requiring physical access to hardware
- Social engineering attacks targeting project maintainers
- Denial of service that requires significant resources (volumetric DDoS)
- Theoretical vulnerabilities without a working proof of concept
- Issues in third-party dependencies that have no available patch (please report upstream)

---

## Responsible Disclosure Process

We follow a coordinated vulnerability disclosure process:

1. **Report received**: We acknowledge receipt of your report.
2. **Triage**: We assess severity, scope, and reproducibility.
3. **Confirmation**: We confirm the vulnerability and communicate our findings to you.
4. **Remediation**: We develop and test a fix.
5. **Release**: We publish a patched release.
6. **Disclosure**: We publish a security advisory (GitHub Security Advisory or CVE) after the fix is available.
7. **Credit**: With your permission, we credit you in the advisory and CHANGELOG.

---

## SLA Commitments

We commit to the following response times:

| Severity | Acknowledgment | Status Update | Target Patch Release |
|----------|---------------|---------------|---------------------|
| Critical (CVSS ≥ 9.0) | 24 hours | 72 hours | 7 calendar days |
| High (CVSS 7.0–8.9) | 48 hours | 5 business days | 14 calendar days |
| Medium (CVSS 4.0–6.9) | 7 calendar days | 14 calendar days | 30 calendar days |
| Low (CVSS < 4.0) | 14 calendar days | 30 calendar days | Next minor release |

These are **target** commitments, not guarantees. Complexity of the fix, patch coordination with dependencies, and availability of maintainers can affect actual timelines. We will communicate any delays proactively.

---

## Security Best Practices for Operators

When deploying this platform, please follow these security guidelines:

### GCP IAM
- Use Workload Identity Federation instead of service account key files
- Apply the principle of least privilege to all service accounts
- Avoid `roles/owner` or `roles/editor` bindings; prefer fine-grained roles
- Regularly audit IAM policies with Policy Analyzer

### Secrets Management
- Store all secrets in GCP Secret Manager, not in environment variables or `.env` files in production
- Rotate `JWT_SECRET_KEY` and `GITHUB_TOKEN` at least every 90 days
- Never commit `.env` files to source control

### Network Security
- Deploy the API service behind Cloud Load Balancer with Cloud Armor WAF rules
- Restrict database and Redis access to the GKE cluster's VPC
- Enable Private Google Access for all subnets
- Use VPC Service Controls to restrict Vertex AI and other API access

### Terraform State
- Store Terraform state in a GCS bucket with versioning enabled and uniform bucket-level access
- Enable audit logging on the GCS state bucket
- Restrict state bucket access to CI/CD service accounts only

### Container Security
- Use the pinned image digests in production Kubernetes manifests
- Enable GKE Binary Authorization to enforce image signing
- Run containers as non-root with a read-only filesystem where possible
- Enable GKE Workload Identity

### IaC Policy
- Review all agent-generated Terraform before applying, especially in production
- Configure `CHECKOV_SKIP_CHECKS` conservatively; never skip security-critical checks
- Require manual approval gates in the Terraform CI workflow for production environments

---

## Security Advisories

Security advisories for this project are published at:
[https://github.com/kogunlowo123/agentic-infrastructure-engineering/security/advisories](https://github.com/kogunlowo123/agentic-infrastructure-engineering/security/advisories)

---

## Third-Party Security Reports

If you discover a vulnerability in a dependency of this project, please report it to the upstream project directly and also inform us so we can update the dependency promptly.

Key dependencies and their security contacts:
- **FastAPI**: [https://github.com/fastapi/fastapi/security](https://github.com/fastapi/fastapi/security)
- **LangGraph / LangChain**: [security@langchain.dev](mailto:security@langchain.dev)
- **LiteLLM**: [https://github.com/BerriAI/litellm/security](https://github.com/BerriAI/litellm/security)
- **Terraform**: [https://www.hashicorp.com/security](https://www.hashicorp.com/security)

---

*This security policy was last updated: 2024-01-01*
