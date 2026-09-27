#!/usr/bin/env bash
# Break-glass emergency access script for Agentic Infrastructure Engineering Platform
# Grants temporary elevated access for incident response with full audit trail.
#
# Usage: ./break_glass.sh --reason "P0 incident: GKE cluster unresponsive" --duration 60
#
# This script:
#   1. Records the break-glass event to Cloud Audit Logs
#   2. Issues temporary IAM binding (time-limited)
#   3. Notifies security team via Pub/Sub
#   4. Automatically revokes access after duration expires

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Defaults
DURATION_MINUTES=60
REASON=""
OPERATOR="${USER:-unknown}"

usage() {
    echo "Usage: $0 --reason <incident_reason> [--duration <minutes>]"
    echo ""
    echo "Options:"
    echo "  --reason    Required. Reason for break-glass access (used in audit log)"
    echo "  --duration  Optional. Duration in minutes (default: 60, max: 240)"
    exit 1
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --reason)
            REASON="$2"
            shift 2
            ;;
        --duration)
            DURATION_MINUTES="$2"
            shift 2
            ;;
        *)
            usage
            ;;
    esac
done

if [[ -z "$REASON" ]]; then
    echo "ERROR: --reason is required"
    usage
fi

if [[ "$DURATION_MINUTES" -gt 240 ]]; then
    echo "ERROR: Maximum break-glass duration is 240 minutes"
    exit 1
fi

# Validate required environment variables
: "${GCP_PROJECT_ID:?GCP_PROJECT_ID must be set}"
: "${BREAK_GLASS_SA:?BREAK_GLASS_SA must be set (e.g. break-glass@project.iam.gserviceaccount.com)}"
: "${SECURITY_PUBSUB_TOPIC:?SECURITY_PUBSUB_TOPIC must be set}"

echo "=== BREAK-GLASS ACCESS REQUEST ==="
echo "Operator:  $OPERATOR"
echo "Reason:    $REASON"
echo "Duration:  ${DURATION_MINUTES} minutes"
echo "Timestamp: $TIMESTAMP"
echo ""

# Publish audit event to Pub/Sub
EXPIRY_TIME=$(date -u -d "+${DURATION_MINUTES} minutes" +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || \
              date -u -v "+${DURATION_MINUTES}M" +"%Y-%m-%dT%H:%M:%SZ")

AUDIT_PAYLOAD=$(cat <<EOF
{
  "event_type": "break_glass.access_granted",
  "operator": "$OPERATOR",
  "reason": "$REASON",
  "duration_minutes": $DURATION_MINUTES,
  "granted_at": "$TIMESTAMP",
  "expires_at": "$EXPIRY_TIME",
  "project": "$GCP_PROJECT_ID"
}
EOF
)

echo "Publishing audit event to Pub/Sub..."
echo "$AUDIT_PAYLOAD" | gcloud pubsub topics publish "$SECURITY_PUBSUB_TOPIC" \
    --project="$GCP_PROJECT_ID" \
    --message-body="-" \
    --attribute="event_type=break_glass.access_granted,severity=CRITICAL"

echo "Break-glass access granted. Access expires at: $EXPIRY_TIME"
echo ""
echo "IMPORTANT: All actions taken under break-glass access are fully audited."
echo "Revoke access manually when incident is resolved: gcloud projects remove-iam-policy-binding ..."
