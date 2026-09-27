"""T2 approval gate management."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Literal

import psycopg2
import psycopg2.extras

logger = logging.getLogger(__name__)

ApprovalDecision = Literal["approved", "rejected", "pending"]

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS approval_requests (
    request_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id      TEXT NOT NULL,
    pr_url          TEXT,
    pr_number       INT,
    requested_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    decided_at      TIMESTAMPTZ,
    decision        TEXT CHECK (decision IN ('approved', 'rejected', 'pending')),
    decided_by      TEXT,
    metadata        JSONB
);

CREATE INDEX IF NOT EXISTS approval_requests_session_idx ON approval_requests (session_id);
"""


class ApprovalGate:
    """Manages T2 approval requests stored in PostgreSQL."""

    def __init__(self, database_url: str) -> None:
        self._database_url = database_url
        self._ensure_schema()

    def _connect(self) -> psycopg2.extensions.connection:
        return psycopg2.connect(self._database_url)

    def _ensure_schema(self) -> None:
        try:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(CREATE_TABLE_SQL)
                conn.commit()
        except Exception as exc:
            logger.warning("Could not ensure approval schema: %s", exc)

    def create_request(
        self,
        session_id: str,
        pr_url: str | None = None,
        pr_number: int | None = None,
        metadata: dict | None = None,
    ) -> str:
        """Create an approval request and return the request ID."""
        request_id = str(uuid.uuid4())
        try:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO approval_requests
                            (request_id, session_id, pr_url, pr_number, decision, metadata)
                        VALUES (%s, %s, %s, %s, 'pending', %s)
                        """,
                        (
                            request_id,
                            session_id,
                            pr_url,
                            pr_number,
                            psycopg2.extras.Json(metadata or {}),
                        ),
                    )
                conn.commit()
        except Exception as exc:
            logger.error("Failed to create approval request: %s", exc)
        return request_id

    def decide(
        self,
        request_id: str,
        decision: ApprovalDecision,
        decided_by: str = "system",
    ) -> bool:
        """Record an approval or rejection decision."""
        try:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE approval_requests
                        SET decision = %s, decided_at = NOW(), decided_by = %s
                        WHERE request_id = %s AND decision = 'pending'
                        """,
                        (decision, decided_by, request_id),
                    )
                    updated = cur.rowcount
                conn.commit()
            return updated > 0
        except Exception as exc:
            logger.error("Failed to record decision: %s", exc)
            return False

    def get_status(self, session_id: str) -> ApprovalDecision:
        """Get the current approval status for a session."""
        try:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT decision FROM approval_requests WHERE session_id = %s ORDER BY requested_at DESC LIMIT 1",
                        (session_id,),
                    )
                    row = cur.fetchone()
                    if row:
                        return row[0]
        except Exception as exc:
            logger.warning("Failed to get approval status: %s", exc)
        return "pending"
