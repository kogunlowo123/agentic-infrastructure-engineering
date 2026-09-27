# Makefile for Agentic Infrastructure Engineering Platform
# Usage: make <target>
# Run `make help` to see all available targets.

# ----- Configuration -------------------------------------------------------

PYTHON_VERSION  := 3.12
UV              := uv
DOCKER          := docker
DOCKER_COMPOSE  := docker compose
TERRAFORM       := terraform
CHECKOV         := checkov

# GCP configuration (override via environment or CLI flags)
GCP_PROJECT_ID  ?= $(shell cat .env 2>/dev/null | grep GCP_PROJECT_ID | cut -d= -f2)
GCP_REGION      ?= us-central1
IMAGE_TAG       ?= $(shell git describe --tags --always --dirty 2>/dev/null || echo "dev")
REGISTRY        ?= $(GCP_REGION)-docker.pkg.dev/$(GCP_PROJECT_ID)/agentic-infra

SERVICES        := api agent-runtime rag-core
INFRA_ENVS      := dev staging production

# ----- Colors --------------------------------------------------------------

RESET   := \033[0m
BOLD    := \033[1m
GREEN   := \033[32m
YELLOW  := \033[33m
CYAN    := \033[36m

# ----- Phony targets -------------------------------------------------------

.PHONY: help install dev lint format typecheck test test-unit test-integration \
        coverage docker-build docker-push docker-pull clean \
        terraform-init terraform-validate terraform-plan terraform-apply \
        terraform-fmt pre-commit-install pre-commit-run docs-serve

# ----- Default target ------------------------------------------------------

.DEFAULT_GOAL := help

# ----- Help ----------------------------------------------------------------

help: ## Show this help message
	@echo ""
	@echo "$(BOLD)Agentic Infrastructure Engineering — Make Targets$(RESET)"
	@echo ""
	@echo "$(CYAN)Development$(RESET)"
	@grep -E '^(install|dev|lint|format|typecheck|test|test-unit|test-integration|coverage|pre-commit-install|pre-commit-run):.*##' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*##"}; {printf "  $(GREEN)%-28s$(RESET) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(CYAN)Docker$(RESET)"
	@grep -E '^(docker-build|docker-push|docker-pull):.*##' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*##"}; {printf "  $(GREEN)%-28s$(RESET) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(CYAN)Terraform$(RESET)"
	@grep -E '^(terraform-init|terraform-validate|terraform-plan|terraform-apply|terraform-fmt):.*##' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*##"}; {printf "  $(GREEN)%-28s$(RESET) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(CYAN)Other$(RESET)"
	@grep -E '^(clean|docs-serve):.*##' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*##"}; {printf "  $(GREEN)%-28s$(RESET) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(YELLOW)Override variables:$(RESET)"
	@echo "  GCP_PROJECT_ID   GCP project ID (default: from .env)"
	@echo "  GCP_REGION       GCP region (default: us-central1)"
	@echo "  IMAGE_TAG        Docker image tag (default: git describe)"
	@echo "  REGISTRY         Artifact Registry path"
	@echo "  TF_ENV           Terraform environment: dev|staging|production (default: dev)"
	@echo ""

# ----- Development ---------------------------------------------------------

install: pre-commit-install ## Install all service dependencies and dev tooling
	@echo "$(CYAN)Installing dependencies for all services...$(RESET)"
	$(UV) sync --all-extras --directory services/api
	$(UV) sync --all-extras --directory services/agent-runtime
	$(UV) sync --all-extras --directory services/rag-core
	@echo "$(GREEN)Installation complete.$(RESET)"

dev: ## Start the full local development stack via Docker Compose
	@if [ ! -f docker-compose.override.yml ]; then \
		echo "$(YELLOW)No docker-compose.override.yml found. Copying example...$(RESET)"; \
		cp docker-compose.override.example.yml docker-compose.override.yml; \
	fi
	@if [ ! -f .env ]; then \
		echo "$(YELLOW)No .env file found. Copying .env.example...$(RESET)"; \
		cp .env.example .env; \
	fi
	$(DOCKER_COMPOSE) up -d --build
	@echo ""
	@echo "$(GREEN)Development stack is running.$(RESET)"
	@echo "  API:         http://localhost:8000"
	@echo "  API Docs:    http://localhost:8000/docs"
	@echo "  Postgres:    localhost:5432"
	@echo "  OpenSearch:  http://localhost:9200"
	@echo "  Redis:       localhost:6379"
	@echo ""
	@echo "Run '$(DOCKER_COMPOSE) logs -f' to tail logs."

# ----- Linting & Formatting ------------------------------------------------

lint: ## Run ruff linter and mypy type checker
	@echo "$(CYAN)Running ruff...$(RESET)"
	@for svc in $(SERVICES); do \
		echo "  → services/$$svc"; \
		$(UV) run --directory services/$$svc ruff check src/ tests/; \
	done
	@echo "$(CYAN)Running mypy...$(RESET)"
	@for svc in $(SERVICES); do \
		echo "  → services/$$svc"; \
		$(UV) run --directory services/$$svc mypy src/; \
	done
	@echo "$(GREEN)Lint passed.$(RESET)"

format: ## Auto-format code with black and ruff --fix
	@echo "$(CYAN)Running black...$(RESET)"
	@for svc in $(SERVICES); do \
		$(UV) run --directory services/$$svc black src/ tests/; \
	done
	@echo "$(CYAN)Running ruff --fix...$(RESET)"
	@for svc in $(SERVICES); do \
		$(UV) run --directory services/$$svc ruff check --fix src/ tests/; \
	done
	@echo "$(GREEN)Format complete.$(RESET)"

typecheck: ## Run mypy strict type checking across all services
	@echo "$(CYAN)Running mypy (strict)...$(RESET)"
	@for svc in $(SERVICES); do \
		echo "  → services/$$svc"; \
		$(UV) run --directory services/$$svc mypy --strict src/; \
	done
	@echo "$(GREEN)Type check passed.$(RESET)"

# ----- Testing -------------------------------------------------------------

test: test-unit test-integration ## Run unit and integration tests

test-unit: ## Run unit tests (no external dependencies)
	@echo "$(CYAN)Running unit tests...$(RESET)"
	@for svc in $(SERVICES); do \
		echo "$(BOLD)  → services/$$svc$(RESET)"; \
		$(UV) run --directory services/$$svc pytest tests/unit/ \
			-v \
			--tb=short \
			--cov=src \
			--cov-report=term-missing \
			--cov-fail-under=80; \
	done
	@echo "$(GREEN)Unit tests passed.$(RESET)"

test-integration: ## Run integration tests (requires Docker Compose stack)
	@echo "$(CYAN)Checking Docker Compose stack...$(RESET)"
	@$(DOCKER_COMPOSE) ps --services --filter status=running | grep -q api || \
		(echo "$(YELLOW)Stack not running. Starting...$(RESET)" && $(DOCKER_COMPOSE) up -d)
	@echo "$(CYAN)Running integration tests...$(RESET)"
	@for svc in $(SERVICES); do \
		echo "$(BOLD)  → services/$$svc$(RESET)"; \
		$(UV) run --directory services/$$svc pytest tests/integration/ \
			-v \
			--tb=short \
			-m integration; \
	done
	@echo "$(GREEN)Integration tests passed.$(RESET)"

coverage: ## Generate HTML coverage report
	@for svc in $(SERVICES); do \
		$(UV) run --directory services/$$svc pytest tests/ \
			--cov=src \
			--cov-report=html:htmlcov/$$svc \
			--cov-report=xml:coverage-$$svc.xml; \
	done
	@echo "$(GREEN)Coverage reports written to htmlcov/$(RESET)"

# ----- Docker --------------------------------------------------------------

docker-build: ## Build Docker images for all services
	@echo "$(CYAN)Building Docker images (tag: $(IMAGE_TAG))...$(RESET)"
	@for svc in $(SERVICES); do \
		echo "  → $$svc"; \
		$(DOCKER) build \
			--tag $(REGISTRY)/$$svc:$(IMAGE_TAG) \
			--tag $(REGISTRY)/$$svc:latest \
			--build-arg BUILD_DATE=$$(date -u +%Y-%m-%dT%H:%M:%SZ) \
			--build-arg GIT_COMMIT=$$(git rev-parse --short HEAD 2>/dev/null || echo unknown) \
			--file services/$$svc/Dockerfile \
			services/$$svc; \
	done
	@echo "$(GREEN)Docker build complete.$(RESET)"

docker-push: ## Push Docker images to GCP Artifact Registry
	@if [ -z "$(GCP_PROJECT_ID)" ]; then \
		echo "$(YELLOW)ERROR: GCP_PROJECT_ID is not set.$(RESET)"; exit 1; \
	fi
	@echo "$(CYAN)Pushing Docker images (tag: $(IMAGE_TAG))...$(RESET)"
	@gcloud auth configure-docker $(GCP_REGION)-docker.pkg.dev --quiet
	@for svc in $(SERVICES); do \
		echo "  → $$svc"; \
		$(DOCKER) push $(REGISTRY)/$$svc:$(IMAGE_TAG); \
		$(DOCKER) push $(REGISTRY)/$$svc:latest; \
	done
	@echo "$(GREEN)Docker push complete.$(RESET)"

docker-pull: ## Pull latest Docker images from Artifact Registry
	@for svc in $(SERVICES); do \
		$(DOCKER) pull $(REGISTRY)/$$svc:latest || true; \
	done

# ----- Terraform -----------------------------------------------------------

TF_ENV       ?= dev
TF_DIR       := infra/gcp/environments/$(TF_ENV)
TF_PLAN_FILE := $(TF_ENV).tfplan

terraform-init: ## Initialize Terraform for a given environment (TF_ENV=dev|staging|production)
	@echo "$(CYAN)Initializing Terraform for environment: $(TF_ENV)$(RESET)"
	cd $(TF_DIR) && $(TERRAFORM) init -upgrade
	@echo "$(GREEN)Terraform init complete.$(RESET)"

terraform-validate: terraform-fmt ## Validate Terraform configuration
	@echo "$(CYAN)Validating Terraform...$(RESET)"
	@for env in $(INFRA_ENVS); do \
		echo "  → infra/gcp/environments/$$env"; \
		cd infra/gcp/environments/$$env && $(TERRAFORM) validate && cd - > /dev/null; \
	done
	@echo "$(GREEN)Validation passed.$(RESET)"

terraform-fmt: ## Format all Terraform files
	@echo "$(CYAN)Formatting Terraform...$(RESET)"
	$(TERRAFORM) fmt -recursive infra/
	@echo "$(GREEN)Terraform format complete.$(RESET)"

terraform-plan: terraform-init ## Generate a Terraform execution plan
	@echo "$(CYAN)Planning Terraform for environment: $(TF_ENV)$(RESET)"
	cd $(TF_DIR) && $(TERRAFORM) plan -out=$(TF_PLAN_FILE)
	@echo "$(GREEN)Plan written to $(TF_DIR)/$(TF_PLAN_FILE)$(RESET)"

terraform-apply: ## Apply Terraform plan (requires prior terraform-plan)
	@if [ ! -f "$(TF_DIR)/$(TF_PLAN_FILE)" ]; then \
		echo "$(YELLOW)No plan file found. Run 'make terraform-plan TF_ENV=$(TF_ENV)' first.$(RESET)"; \
		exit 1; \
	fi
	@if [ "$(TF_ENV)" = "production" ]; then \
		echo "$(YELLOW)WARNING: You are about to apply to PRODUCTION.$(RESET)"; \
		read -p "Type 'yes' to confirm: " confirm && [ "$$confirm" = "yes" ] || exit 1; \
	fi
	@echo "$(CYAN)Applying Terraform for environment: $(TF_ENV)$(RESET)"
	cd $(TF_DIR) && $(TERRAFORM) apply $(TF_PLAN_FILE)
	@echo "$(GREEN)Terraform apply complete.$(RESET)"

# ----- Pre-commit ----------------------------------------------------------

pre-commit-install: ## Install pre-commit hooks
	@which pre-commit > /dev/null 2>&1 || pip install pre-commit
	pre-commit install
	@echo "$(GREEN)Pre-commit hooks installed.$(RESET)"

pre-commit-run: ## Run all pre-commit hooks against all files
	pre-commit run --all-files

# ----- Documentation -------------------------------------------------------

docs-serve: ## Serve documentation locally with mkdocs
	$(UV) run mkdocs serve --dev-addr 0.0.0.0:8080

# ----- Cleanup -------------------------------------------------------------

clean: ## Remove build artifacts, caches, and temporary files
	@echo "$(CYAN)Cleaning build artifacts...$(RESET)"
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "dist" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -name "coverage*.xml" -delete 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	find . -name "*.tfplan" -delete 2>/dev/null || true
	$(DOCKER_COMPOSE) down --volumes --remove-orphans 2>/dev/null || true
	@echo "$(GREEN)Clean complete.$(RESET)"
