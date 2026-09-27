# ADR 0002: Drift Detection Method

## Status

Accepted

## Date

2024-01-01

## Context

Infrastructure drift occurs when the actual GCP resource state diverges from
the Terraform state file. The platform must:

- Detect drift automatically and classify severity (none/low/medium/high/critical)
- Generate human-readable drift reports with remediation commands
- Operate without applying Terraform (read-only, T1 tier)
- Support periodic polling and event-driven detection via Pub/Sub

## Decision

Use a LangGraph `StateGraph` for drift detection:

1. `fetch_terraform_state` — Parse the Terraform plan JSON (`terraform plan -json`)
   which contains `resource_drift` blocks comparing prior vs. current state
2. `compare_state_plan` — Iterate drift items; classify each by resource type
   and attribute change pattern; assign severity per item and aggregate
3. `generate_drift_report` — Format findings into a structured `DriftReport`
   with `remediation_commands` (`terraform apply -target=<resource>`)

**Severity classification rules:**
- `critical`: Security groups, IAM bindings, KMS key deletion
- `high`: Compute instance type, GKE node pool size
- `medium`: Labels, tags, metadata
- `low`: Description fields, non-functional attributes

The `terraform plan -json` output is used rather than direct GCP API calls because:
- It leverages Terraform's own provider-aware comparison logic
- Avoids reimplementing GCP resource diffing for hundreds of resource types
- Produces `resource_drift` blocks with `before`/`after` attribute diffs

## Alternatives Considered

### Direct GCP API polling
Rejected: requires per-resource-type implementation; high maintenance burden;
doesn't model multi-resource interdependencies.

### Cloud Asset Inventory comparison
Viable but complementary: CAI exports lag behind real-time state; Terraform plan
is already the source of truth for managed resources.

### Continuous streaming from Cloud Audit Logs
Complementary (Sigma rule `drift-anomaly.yml` covers this); plan-based detection
is the authoritative method for structured reports.

## Consequences

- `terraform plan -json` must be provided by the caller (not executed by the platform)
  to avoid granting Terraform apply permissions to T1 agents
- Drift detection latency depends on when the caller runs `terraform plan`; not real-time
- Severity classification is heuristic and may need tuning per organization
