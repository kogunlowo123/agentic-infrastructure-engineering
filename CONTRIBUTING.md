# Contributing to Agentic Infrastructure Engineering

Thank you for your interest in contributing to this project! This guide covers everything you need to know to contribute effectively.

---

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Workflow](#development-workflow)
- [Code Standards](#code-standards)
- [Testing Requirements](#testing-requirements)
- [Commit Message Convention](#commit-message-convention)
- [Pull Request Process](#pull-request-process)
- [Infrastructure (Terraform) Contributions](#infrastructure-terraform-contributions)

---

## Code of Conduct

This project follows the [Contributor Covenant Code of Conduct](https://www.contributor-covenant.org/version/2/1/code_of_conduct/). By participating, you agree to uphold this standard. Report unacceptable behavior to [kogunlowo@gmail.com](mailto:kogunlowo@gmail.com).

---

## Getting Started

### Prerequisites

- Python 3.12+
- [uv](https://github.com/astral-sh/uv) (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- Docker & Docker Compose v2
- Terraform 1.8+
- `git` 2.40+
- `pre-commit` (`pip install pre-commit` or `brew install pre-commit`)

### Fork and Clone

1. Fork the repository on GitHub.
2. Clone your fork locally:
   ```bash
   git clone https://github.com/<your-username>/agentic-infrastructure-engineering.git
   cd agentic-infrastructure-engineering
   ```
3. Add the upstream remote:
   ```bash
   git remote add upstream https://github.com/kogunlowo123/agentic-infrastructure-engineering.git
   ```

### Install Dependencies

```bash
make install
```

This installs all service dependencies using `uv`, sets up pre-commit hooks, and verifies your toolchain.

### Configure Local Environment

```bash
cp .env.example .env
# Edit .env — at minimum set GCP_PROJECT_ID and DATABASE_URL
```

### Start the Development Stack

```bash
cp docker-compose.override.example.yml docker-compose.override.yml
make dev
```

---

## Development Workflow

### Branching Strategy

| Branch | Purpose |
|--------|---------|
| `main` | Production-ready code; protected, requires PR + passing CI |
| `develop` | Integration branch for feature development |
| `feature/<name>` | New features and enhancements |
| `fix/<name>` | Bug fixes |
| `chore/<name>` | Tooling, dependencies, CI changes |
| `docs/<name>` | Documentation-only changes |
| `infra/<name>` | Terraform / infrastructure changes |

### Starting a Feature

```bash
# Sync with upstream
git fetch upstream
git checkout main
git merge upstream/main

# Create your branch
git checkout -b feature/my-awesome-feature
```

### During Development

Run the full quality suite before committing:

```bash
make lint      # ruff + mypy
make format    # black + ruff --fix
make test      # unit + integration tests
```

Pre-commit hooks run automatically on `git commit` and catch most issues early.

### Keeping Your Branch Up to Date

```bash
git fetch upstream
git rebase upstream/main
```

---

## Code Standards

### Python

This project enforces strict code quality standards. All Python code must pass:

| Tool | Purpose | Config |
|------|---------|--------|
| `black` | Code formatting | `pyproject.toml` → `[tool.black]` |
| `ruff` | Linting (replaces flake8, isort, pyupgrade) | `pyproject.toml` → `[tool.ruff]` |
| `mypy` | Static type checking (strict mode) | `pyproject.toml` → `[tool.mypy]` |

#### Style Rules

- **Type annotations are mandatory** on all function signatures
- **Docstrings are required** for all public modules, classes, and functions (Google style)
- Maximum line length: **88 characters** (black default)
- Use `from __future__ import annotations` at the top of every Python file
- Prefer `pathlib.Path` over `os.path`
- Use `structlog` for structured logging; do not use `print()` in library/service code
- All I/O operations must be `async`; use `asyncio` and `httpx` throughout

#### Example function signature

```python
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agent_runtime.state import AgentState


async def generate_iac_module(
    intent: str,
    constraints: dict[str, str],
    state: AgentState,
) -> str:
    """Generate a Terraform module from natural language intent.

    Args:
        intent: Natural language description of desired infrastructure.
        constraints: Key-value pairs constraining generation (region, env, labels).
        state: Current LangGraph agent state for context and memory.

    Returns:
        Generated Terraform module as a multi-file archive (base64-encoded tar.gz).

    Raises:
        GenerationError: If the LLM fails to produce valid Terraform.
        PolicyViolationError: If generated code violates organizational policy.
    """
    ...
```

### Terraform

- Follow the [Terraform Style Guide](https://developer.hashicorp.com/terraform/language/style)
- All resources must have `labels` including `managed-by = "terraform"` and `environment`
- Variables must have descriptions and types
- Outputs must have descriptions
- Use `for_each` over `count` for resource collections
- Pin provider versions with `~>` (pessimistic constraint)
- All Terraform must pass `checkov` with no HIGH or CRITICAL findings (unless explicitly justified and suppressed with a comment)

### YAML / JSON

- YAML: 2-space indentation
- JSON: 2-space indentation, no trailing commas
- All workflow files must have comments explaining non-obvious steps

---

## Testing Requirements

### Test Structure

```
services/<service>/tests/
├── unit/           # Fast, no external dependencies
├── integration/    # Require running services (Docker Compose)
└── conftest.py     # Shared fixtures
```

### Requirements

| Test Type | Coverage Requirement | Runs in CI |
|-----------|---------------------|------------|
| Unit | ≥ 80% line coverage for new code | Yes, always |
| Integration | Must cover agent happy path and error paths | Yes, on PR |

### Running Tests

```bash
# All tests
make test

# Unit only (fast)
make test-unit

# Integration (requires Docker Compose stack running)
make test-integration

# With coverage report
uv run pytest services/api/tests/ --cov=src --cov-report=html
```

### Writing Tests

- Use `pytest` and `pytest-asyncio` for async tests
- Use `pytest-mock` for mocking; avoid `unittest.mock` directly
- Use `httpx.AsyncClient` for API integration tests
- Name test functions descriptively: `test_<unit>_<scenario>_<expected_outcome>`
- Every new feature must include at least:
  - A unit test for the core logic
  - An integration test for the API endpoint (if applicable)
  - A test for the error/failure path

Example:
```python
async def test_iac_generator_run_with_valid_intent_returns_terraform_module() -> None:
    ...

async def test_iac_generator_run_with_policy_violation_raises_error() -> None:
    ...
```

---

## Commit Message Convention

This project follows [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/).

### Format

```
<type>(<scope>): <short summary>

[optional body]

[optional footer(s)]
```

### Types

| Type | When to Use |
|------|-------------|
| `feat` | A new feature |
| `fix` | A bug fix |
| `docs` | Documentation only changes |
| `style` | Formatting changes (no logic change) |
| `refactor` | Code change that neither fixes a bug nor adds a feature |
| `perf` | Performance improvement |
| `test` | Adding or updating tests |
| `chore` | Build process, tooling, dependency updates |
| `infra` | Infrastructure (Terraform, Kubernetes) changes |
| `ci` | Changes to CI/CD workflows |
| `security` | Security fixes or improvements |

### Scopes

Use the service or module name: `api`, `agent-runtime`, `rag-core`, `iac-generator`, `drift-detector`, `cost-optimizer`, `infra`, `ci`.

### Examples

```
feat(iac-generator): add GKE autopilot module template

fix(drift-detector): handle nil resource state during scan

chore(deps): upgrade litellm from 1.40.0 to 1.42.0

infra(gcp): add Cloud Armor WAF policy to load balancer

BREAKING CHANGE: The /v1/agents/iac-generator/run endpoint now requires
the `constraints` field in the request body.
```

---

## Pull Request Process

### Before Submitting

- [ ] All commits follow conventional commit format
- [ ] `make lint` passes with no errors
- [ ] `make typecheck` passes with no errors
- [ ] `make test` passes with ≥ 80% coverage on new code
- [ ] Any new environment variables are documented in `.env.example` and `README.md`
- [ ] Any new Terraform resources pass `checkov` with no HIGH/CRITICAL findings
- [ ] Documentation is updated if the behavior changes

### PR Title

Use conventional commit format for the PR title: `feat(scope): description`.

### PR Description

Fill in the pull request template completely. Reviewers will not merge PRs with incomplete templates.

### Review Process

1. Open a PR against `main` (or `develop` for work-in-progress).
2. CI runs automatically: lint, typecheck, unit tests, integration tests, security scans.
3. Request review from `@kogunlowo123`.
4. Address all review comments. Resolve conversations only when the issue is fixed.
5. Once approved and CI passes, the PR can be merged using **squash and merge**.
6. Delete your branch after merge.

### Terraform PRs

Terraform PRs have additional requirements:
- A `terraform plan` output must be included in the PR description (use the CI-generated plan comment)
- For production changes, a manual approval step is required before apply
- Document any resource deletions or state moves explicitly

---

## Infrastructure (Terraform) Contributions

### Module Development

New Terraform modules go in `infra/gcp/modules/<module-name>/`. Each module must include:

- `main.tf` — resource definitions
- `variables.tf` — input variables with types and descriptions
- `outputs.tf` — outputs with descriptions
- `versions.tf` — provider and Terraform version constraints
- `README.md` — usage example, inputs table, outputs table (generated via `terraform-docs`)

### Testing Terraform Modules

Use `terratest` (Go) for automated infrastructure tests in `infra/gcp/modules/<name>/test/`. Tests should:
- Deploy the module to a dedicated GCP test project
- Validate resource properties via GCP API calls
- Tear down all resources after the test

### Checkov Policy

We use [Checkov](https://www.checkov.io/) to enforce IaC security policies. The full policy set is active by default. If you need to suppress a check, add an inline comment with justification:

```hcl
resource "google_storage_bucket" "state" {
  # checkov:skip=CKV_GCP_62:Access logging to a separate bucket creates a circular dependency in bootstrap
  name = "my-state-bucket"
  ...
}
```

---

Thank you for contributing! Every improvement, no matter how small, helps build a more reliable and secure platform.
