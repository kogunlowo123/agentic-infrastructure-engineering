#!/usr/bin/env bash
# IaC rollback script for Agentic Infrastructure Engineering Platform
# Rolls back a Terraform deployment to a previous state version stored in GCS.
#
# Usage: ./rollback_iac.sh --env dev --version 42 [--dry-run]

set -euo pipefail

DRY_RUN=false
ENV=""
VERSION=""

usage() {
    echo "Usage: $0 --env <environment> --version <state_version> [--dry-run]"
    echo ""
    echo "Options:"
    echo "  --env       Required. Environment (dev, staging, prod)"
    echo "  --version   Required. State version number to restore"
    echo "  --dry-run   Optional. Show what would be done without making changes"
    exit 1
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --env)       ENV="$2";     shift 2 ;;
        --version)   VERSION="$2"; shift 2 ;;
        --dry-run)   DRY_RUN=true; shift   ;;
        *)           usage ;;
    esac
done

if [[ -z "$ENV" || -z "$VERSION" ]]; then
    echo "ERROR: --env and --version are required"
    usage
fi

: "${GCP_PROJECT_ID:?GCP_PROJECT_ID must be set}"
: "${TF_STATE_BUCKET:?TF_STATE_BUCKET must be set (e.g. gs://my-project-tf-state)}"

STATE_PREFIX="infra/envs/gcp/${ENV}"
STATE_KEY="${STATE_PREFIX}/default.tfstate"
BACKUP_KEY="${STATE_PREFIX}/default.tfstate.backup.$(date -u +%Y%m%d%H%M%S)"

echo "=== IaC ROLLBACK ==="
echo "Environment: $ENV"
echo "Target version: $VERSION"
echo "State bucket:   $TF_STATE_BUCKET"
echo "Dry run:        $DRY_RUN"
echo ""

# List available versions
echo "Fetching state history..."
gcloud storage ls --long "${TF_STATE_BUCKET}/${STATE_KEY}#*" \
    --project="$GCP_PROJECT_ID" 2>/dev/null || true

if [[ "$DRY_RUN" == "true" ]]; then
    echo "[DRY RUN] Would backup current state to: ${TF_STATE_BUCKET}/${BACKUP_KEY}"
    echo "[DRY RUN] Would restore version ${VERSION} as current state"
    exit 0
fi

# Backup current state
echo "Backing up current state to ${BACKUP_KEY}..."
gcloud storage cp \
    "${TF_STATE_BUCKET}/${STATE_KEY}" \
    "${TF_STATE_BUCKET}/${BACKUP_KEY}" \
    --project="$GCP_PROJECT_ID"

# Restore target version
echo "Restoring state version ${VERSION}..."
gcloud storage cp \
    "${TF_STATE_BUCKET}/${STATE_KEY}#${VERSION}" \
    "${TF_STATE_BUCKET}/${STATE_KEY}" \
    --project="$GCP_PROJECT_ID"

echo ""
echo "State rolled back successfully."
echo "Run 'terraform plan' in infra/envs/gcp/${ENV} to review drift."
echo "Run 'terraform apply' to reconcile infrastructure with restored state."
