"""CloudEvents publisher for GCP Pub/Sub."""

import json
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

EVENT_TYPES: dict[str, str] = {
    "iac_generated": "com.agentic-infra.iac.generated.v1",
    "drift_detected": "com.agentic-infra.drift.detected.v1",
    "cost_anomaly": "com.agentic-infra.cost.anomaly.v1",
}

TOPIC_MAP: dict[str, str] = {
    "iac_generated": "iac-generated",
    "drift_detected": "drift-detected",
    "cost_anomaly": "cost-anomaly",
}


class CloudEventPublisher:
    """Publishes CloudEvents to GCP Pub/Sub topics."""

    def __init__(self, project_id: str | None = None) -> None:
        self._project_id = project_id or os.getenv("GCP_PROJECT_ID", "")
        self._publisher: Any = None

    def _get_publisher(self) -> Any:
        if self._publisher is None:
            try:
                from google.cloud import pubsub_v1  # type: ignore[import]
                self._publisher = pubsub_v1.PublisherClient()
            except ImportError:
                logger.warning("google-cloud-pubsub not installed, events will only be logged")
        return self._publisher

    def publish(
        self,
        event_type: str,
        data: dict,
        session_id: str = "",
        tenant_id: str = "",
    ) -> bool:
        """Publish a CloudEvent to the appropriate Pub/Sub topic.

        Args:
            event_type: One of iac_generated, drift_detected, cost_anomaly.
            data: CloudEvent data payload.
            session_id: Optional session identifier.
            tenant_id: Optional tenant identifier.

        Returns:
            True if published successfully, False otherwise.
        """
        cloud_event: dict[str, Any] = {
            "specversion": "1.0",
            "type": EVENT_TYPES.get(
                event_type, f"com.agentic-infra.{event_type}.v1"
            ),
            "source": "agentic-infrastructure-engineering/agent-runtime",
            "id": str(uuid.uuid4()),
            "time": datetime.now(tz=timezone.utc).isoformat(),
            "datacontenttype": "application/json",
            "data": data,
        }

        if session_id:
            cloud_event["sessionid"] = session_id
        if tenant_id:
            cloud_event["tenantid"] = tenant_id

        logger.info(
            "Publishing CloudEvent type=%s session=%s",
            event_type,
            session_id,
        )

        publisher = self._get_publisher()
        if publisher is None:
            return True  # Log-only mode succeeded

        env = os.getenv("ENVIRONMENT", "dev")
        topic_base = TOPIC_MAP.get(event_type, event_type)
        topic_name = f"{topic_base}-{env}"
        topic_path = publisher.topic_path(self._project_id, topic_name)

        try:
            message_bytes = json.dumps(cloud_event).encode("utf-8")
            future = publisher.publish(topic_path, message_bytes)
            future.result(timeout=10)
            return True
        except Exception as exc:
            logger.error("Failed to publish CloudEvent: %s", exc)
            return False
