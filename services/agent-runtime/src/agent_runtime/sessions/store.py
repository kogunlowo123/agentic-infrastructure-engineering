"""Session state store backed by PostgreSQL."""

import logging

import psycopg2
import psycopg2.extras

logger = logging.getLogger(__name__)

CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS agent_sessions (
    session_id   TEXT PRIMARY KEY,
    agent_id     TEXT NOT NULL,
    tenant_id    TEXT NOT NULL,
    state_json   JSONB NOT NULL DEFAULT '{}',
    status       TEXT NOT NULL DEFAULT 'active',
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""


class SessionStore:
    """Persistent session state storage in PostgreSQL."""

    def __init__(self, database_url: str) -> None:
        self._database_url = database_url
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        try:
            with psycopg2.connect(self._database_url) as conn:
                with conn.cursor() as cur:
                    cur.execute(CREATE_TABLE)
                conn.commit()
        except Exception as exc:
            logger.warning("Session store schema error: %s", exc)

    def save(
        self,
        session_id: str,
        agent_id: str,
        tenant_id: str,
        state: dict,
    ) -> None:
        """Create or update a session's state."""
        try:
            with psycopg2.connect(self._database_url) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO agent_sessions (session_id, agent_id, tenant_id, state_json)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (session_id) DO UPDATE SET
                            state_json = EXCLUDED.state_json,
                            updated_at = NOW()
                        """,
                        (
                            session_id,
                            agent_id,
                            tenant_id,
                            psycopg2.extras.Json(state),
                        ),
                    )
                conn.commit()
        except Exception as exc:
            logger.error("Session save failed: %s", exc)

    def get(self, session_id: str) -> dict | None:
        """Retrieve session record by ID."""
        try:
            with psycopg2.connect(self._database_url) as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    cur.execute(
                        "SELECT * FROM agent_sessions WHERE session_id = %s",
                        (session_id,),
                    )
                    row = cur.fetchone()
                    return dict(row) if row else None
        except Exception as exc:
            logger.error("Session get failed: %s", exc)
            return None

    def update_status(self, session_id: str, status: str) -> None:
        """Update session status."""
        try:
            with psycopg2.connect(self._database_url) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE agent_sessions SET status=%s, updated_at=NOW() WHERE session_id=%s",
                        (status, session_id),
                    )
                conn.commit()
        except Exception as exc:
            logger.error("Session status update failed: %s", exc)
