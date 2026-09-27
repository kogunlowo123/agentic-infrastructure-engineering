"""Episodic memory for long-term agent memory storage in PostgreSQL."""

import logging
from typing import Any

logger = logging.getLogger(__name__)

CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS episodic_memory (
    id          BIGSERIAL PRIMARY KEY,
    agent_id    TEXT NOT NULL,
    event_type  TEXT NOT NULL,
    content     JSONB NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS episodic_memory_agent_idx ON episodic_memory (agent_id, event_type);
"""


class EpisodicMemory:
    """Stores key events and outcomes for long-term agent memory."""

    def __init__(self, database_url: str) -> None:
        self._database_url = database_url
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        try:
            import psycopg2

            with psycopg2.connect(self._database_url) as conn:
                with conn.cursor() as cur:
                    cur.execute(CREATE_TABLE)
                conn.commit()
        except Exception as exc:
            logger.warning("Episodic memory schema error: %s", exc)

    def store(self, agent_id: str, event_type: str, content: dict) -> None:
        """Store an episodic memory event."""
        try:
            import psycopg2
            import psycopg2.extras

            with psycopg2.connect(self._database_url) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "INSERT INTO episodic_memory (agent_id, event_type, content) VALUES (%s, %s, %s)",
                        (agent_id, event_type, psycopg2.extras.Json(content)),
                    )
                conn.commit()
        except Exception as exc:
            logger.warning("Episodic memory store failed: %s", exc)

    def retrieve(
        self,
        agent_id: str,
        event_type: str | None = None,
        limit: int = 10,
    ) -> list[dict]:
        """Retrieve recent episodic memories for an agent."""
        try:
            import psycopg2
            import psycopg2.extras

            with psycopg2.connect(self._database_url) as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    if event_type:
                        cur.execute(
                            "SELECT * FROM episodic_memory WHERE agent_id=%s AND event_type=%s ORDER BY created_at DESC LIMIT %s",
                            (agent_id, event_type, limit),
                        )
                    else:
                        cur.execute(
                            "SELECT * FROM episodic_memory WHERE agent_id=%s ORDER BY created_at DESC LIMIT %s",
                            (agent_id, limit),
                        )
                    return [dict(row) for row in cur.fetchall()]
        except Exception as exc:
            logger.warning("Episodic memory retrieve failed: %s", exc)
            return []
