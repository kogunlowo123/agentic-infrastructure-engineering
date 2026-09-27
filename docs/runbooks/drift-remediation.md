# Runbook: Infrastructure Drift Remediation

## Overview

This runbook guides operators through diagnosing and remediating infrastructure
drift detected by the Agentic Infrastructure Engineering platform.

## Prerequisites

- `gcloud` CLI authenticated with appropriate IAM roles
- `terraform` 1.8+ installed
- Access to the affected GCP project
- Repository cloned locally at `infra/envs/gcp/<env>/`

## Step 1: Review the Drift Report

1. Open the drift notification in Pub/Sub or the API response:
   ```
   GET /api/v1/drift/detect
   ```
2. Note the `severity` field. For `critical` or `high` severity, proceed to
   Step 2 immediately. For `low`/`medium`, schedule remediation within the SLA.

**Severity SLAs:**
| Severity | Maximum Remediation Time |
|----------|-------------------------|
| critical | 4 hours |
| high     | 24 hours |
| medium   | 72 hours |
| low      | 1 week |

## Step 2: Validate the Drift

1. Navigate to the environment directory:
   ```bash
   cd infra/envs/gcp/<env>
   ```
2. Run `terraform plan` to confirm current drift:
   ```bash
   terraform plan -out=drift-remediation.tfplan
   ```
3. Review the plan output. Confirm the drift matches the report.

## Step 3: Remediate

### Option A: Apply via CI/CD (preferred)

1. Create a remediation PR:
   ```bash
   git checkout -b fix/drift-remediation-$(date +%Y%m%d)
   # Make no code changes — the drift is in the actual resources
   git push origin fix/drift-remediation-$(date +%Y%m%d)
   ```
2. Open a PR; the `terraform.yml` workflow runs `terraform plan` in CI
3. After T2 approval, merge; CD pipeline runs `terraform apply`

### Option B: Targeted apply (emergency)

For critical severity requiring immediate remediation:
```bash
terraform apply -target=<resource_address> drift-remediation.tfplan
```

Log the emergency change:
```bash
./deploy/scripts/break_glass.sh \
  --reason "Critical drift on <resource>: <description>" \
  --duration 60
```

## Step 4: Verify Remediation

1. Re-run drift detection:
   ```
   POST /api/v1/drift/detect
   ```
2. Confirm `total_drifted: 0` and `severity: none`.
3. Close any open incidents.

## Escalation

If drift cannot be remediated within SLA:
1. Escalate to platform team via PagerDuty (P1/P2 severity)
2. Open GitHub issue using the `security-finding` template if drift involves
   IAM or security group changes
3. Notify security team at kogunlowo@gmail.com for critical severity
