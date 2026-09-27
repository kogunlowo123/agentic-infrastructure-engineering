## Summary

<!-- Provide a concise description of the changes in this PR and why they were made. -->
<!-- Link to any related issue(s): Closes #NNN -->



## Type of Change

<!-- Check all that apply: -->

- [ ] `feat` — New feature or capability
- [ ] `fix` — Bug fix
- [ ] `refactor` — Code refactor (no feature change, no bug fix)
- [ ] `perf` — Performance improvement
- [ ] `test` — Adding or updating tests
- [ ] `docs` — Documentation only
- [ ] `chore` — Build, tooling, or dependency update
- [ ] `infra` — Terraform / Kubernetes / infrastructure change
- [ ] `ci` — CI/CD pipeline change
- [ ] `security` — Security fix or improvement
- [ ] **BREAKING CHANGE** — Requires migration steps (describe below)

### Breaking Change Description

<!-- If this is a breaking change, describe what breaks and how to migrate. -->



---

## Testing Checklist

<!-- Check each item as you verify it before submitting. -->

- [ ] Unit tests pass locally (`make test-unit`)
- [ ] Integration tests pass locally (`make test-integration`)
- [ ] New code has unit tests with ≥ 80% coverage
- [ ] No new linting errors (`make lint`)
- [ ] Type checking passes (`make typecheck`)
- [ ] Pre-commit hooks pass (`pre-commit run --all-files`)

---

## IaC Review Checklist

<!-- Complete this section only for PRs that include Terraform changes (infra/**). -->
<!-- Skip this section entirely if no Terraform files were modified. -->

- [ ] `terraform fmt` applied (`make terraform-fmt`)
- [ ] `terraform validate` passes for all modified environments
- [ ] `terraform plan` output has been reviewed and pasted below (or linked to CI run)
- [ ] No resources are being **deleted** unintentionally (destructive changes are explicitly called out)
- [ ] State file is **not** modified or committed
- [ ] `checkov` scan passes with no new HIGH or CRITICAL findings
- [ ] All new resources have required labels (`environment`, `managed-by`, `team`)
- [ ] Provider versions are pinned with `~>` constraints
- [ ] No hardcoded secrets or project IDs (use variables)
- [ ] Any `checkov:skip` suppressions have an inline justification comment

### Terraform Plan Output

<details>
<summary>Click to expand terraform plan output</summary>

```
Paste terraform plan output here, or link to the CI workflow run.
```

</details>

---

## Security Checklist

<!-- All PRs must review this section. -->

- [ ] No secrets, credentials, or PII are committed (including in test fixtures)
- [ ] No new external network exposure introduced (e.g., open firewall rules, public storage buckets)
- [ ] Dependencies added/updated have been checked for known CVEs
- [ ] Any new API endpoints have authentication and authorization applied
- [ ] Input validation is applied to all user-controlled inputs
- [ ] Sensitive data is not logged at DEBUG level or above

---

## Deployment Notes

<!-- Describe any actions required at deployment time (DB migrations, config changes, etc.). -->

- [ ] No deployment steps required
- [ ] Requires database migration (`alembic upgrade head`)
- [ ] Requires new environment variable(s) — see `.env.example` updates
- [ ] Requires infrastructure change before/after code deployment (describe):



---

## Screenshots / Evidence

<!-- If applicable, add screenshots, logs, or test output to demonstrate the change works. -->
