"""Idempotency management to prevent duplicate agent operations."""

import logging

import psycopg2
import psycopg2.extras

logger = logging.getLogger(__name__)

CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS idempotency_keys (
    idempotency_key TEXT PRIMARY KEY,
    result_json     JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at      TIMESTAMPTZ NOT NULL DEFAULT NOW() + INTERVAL '24 hours'
);
"""


class IdempotencyManager:
    """Prevents duplicate API operations using idempotency keys stored in PostgreSQL."""

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
            logger.warning("Idempotency schema error: %s", exc)

    def check_and_store(self, key: str, result: dict) -> dict | None:
        """Check if key exists (cached result) or store new result.

        Args:
            key: Idempotency key for the operation.
            result: Result to cache if key is new.

        Returns:
            Cached result if key existed, None if key was new (result stored).
        """
        try:
            with psycopg2.connect(self._database_url) as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    cur.execute(
                        "SELECT result_json FROM idempotency_keys "
                        "WHERE idempotency_key = %s AND expires_at > NOW()",
                        (key,),
                    )
                    row = cur.fetchone()
                    if row:
                        return dict(row["result_json"])

                    cur.execute(
                        "INSERT INTO idempotency_keys (idempotency_key, result_json) "
                        "VALUES (%s, %s) ON CONFLICT DO NOTHING",
                        (key, psycopg2.extras.Json(result)),
                    )
                conn.commit()
            return None
        except Exception as exc:
            logger.warning("Idempotency check failed: %s", exc)
            return None
