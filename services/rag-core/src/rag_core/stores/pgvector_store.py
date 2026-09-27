"""PostgreSQL + pgvector store for document embeddings."""

import json
import logging
import uuid
from contextlib import contextmanager
from typing import Generator

import numpy as np
import psycopg2
import psycopg2.pool
from psycopg2.extras import execute_values

from .vector_base import SearchResult, VectorStore

logger = logging.getLogger(__name__)

CREATE_TABLE_SQL = """
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS iac_documents (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chunk_id    TEXT UNIQUE NOT NULL,
    content     TEXT NOT NULL,
    metadata    JSONB NOT NULL DEFAULT '{}',
    embedding   vector(1024),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS iac_documents_embedding_idx
    ON iac_documents USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

CREATE INDEX IF NOT EXISTS iac_documents_metadata_idx
    ON iac_documents USING GIN (metadata);
"""


class PgVectorStore(VectorStore):
    """Vector store backed by PostgreSQL with pgvector extension.

    Supports cosine similarity search and metadata filtering.
    """

    def __init__(
        self,
        database_url: str,
        collection: str = "iac_documents",
        pool_size: int = 5,
        max_overflow: int = 10,
    ) -> None:
        self._database_url = database_url
        self._collection = collection
        self._pool = psycopg2.pool.ThreadedConnectionPool(
            minconn=1,
            maxconn=pool_size + max_overflow,
            dsn=database_url,
        )
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        """Create table and indexes if they don't exist."""
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(CREATE_TABLE_SQL)
            conn.commit()

    @contextmanager
    def _get_conn(self) -> Generator[psycopg2.extensions.connection, None, None]:
        conn = self._pool.getconn()
        try:
            yield conn
        except Exception:
            conn.rollback()
            raise
        finally:
            self._pool.putconn(conn)

    def upsert(
        self,
        chunk_ids: list[str],
        contents: list[str],
        embeddings: np.ndarray,
        metadatas: list[dict],
    ) -> None:
        """Upsert document chunks with embeddings.

        Args:
            chunk_ids: Unique chunk identifiers.
            contents: Text content for each chunk.
            embeddings: Embedding matrix (n, 1024).
            metadatas: Metadata dicts for each chunk.
        """
        if not chunk_ids:
            return

        records = [
            (
                chunk_ids[i],
                contents[i],
                json.dumps(metadatas[i]),
                embeddings[i].tolist(),
            )
            for i in range(len(chunk_ids))
        ]

        sql = """
            INSERT INTO iac_documents (chunk_id, content, metadata, embedding)
            VALUES %s
            ON CONFLICT (chunk_id) DO UPDATE SET
                content    = EXCLUDED.content,
                metadata   = EXCLUDED.metadata,
                embedding  = EXCLUDED.embedding,
                updated_at = NOW()
        """

        with self._get_conn() as conn:
            with conn.cursor() as cur:
                execute_values(
                    cur,
                    sql,
                    records,
                    template="(%s, %s, %s::jsonb, %s::vector)",
                )
            conn.commit()

        logger.debug("Upserted %d chunks to pgvector", len(chunk_ids))

    def search(
        self,
        query_embedding: np.ndarray,
        top_k: int = 10,
        filters: dict | None = None,
    ) -> list[SearchResult]:
        """Search for similar documents using cosine similarity.

        Args:
            query_embedding: Query vector.
            top_k: Number of results.
            filters: Optional JSONB filters, e.g. {"doc_type": "terraform"}.

        Returns:
            Ranked list of SearchResult.
        """
        where_clauses: list[str] = []
        filter_params: list = []

        if filters:
            for key, value in filters.items():
                where_clauses.append(f"metadata->>'{key}' = %s")
                filter_params.append(str(value))

        where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""
        vec = query_embedding.tolist()

        sql = f"""
            SELECT
                chunk_id,
                content,
                metadata,
                1 - (embedding <=> %s::vector) AS score
            FROM iac_documents
            {where_sql}
            ORDER BY embedding <=> %s::vector
            LIMIT %s
        """

        full_params = [vec] + filter_params + [vec, top_k]

        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, full_params)
                rows = cur.fetchall()

        results = []
        for row in rows:
            chunk_id, content, metadata, score = row
            results.append(
                SearchResult(
                    content=content,
                    metadata=metadata if isinstance(metadata, dict) else json.loads(metadata),
                    score=float(score),
                    chunk_id=chunk_id,
                    source="pgvector",
                )
            )

        return results

    def delete(self, chunk_ids: list[str]) -> None:
        """Delete chunks by ID."""
        if not chunk_ids:
            return
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM iac_documents WHERE chunk_id = ANY(%s)",
                    (chunk_ids,),
                )
            conn.commit()

    def count(self) -> int:
        """Return total document count."""
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM iac_documents")
                row = cur.fetchone()
        return row[0] if row else 0

    def close(self) -> None:
        """Close the connection pool."""
        self._pool.closeall()
