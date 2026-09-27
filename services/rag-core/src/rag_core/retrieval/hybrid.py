"""Hybrid retriever combining PgVector and OpenSearch results with RRF."""

import logging

import numpy as np

from ..embeddings.base import EmbeddingModel
from ..stores.opensearch_store import OpenSearchStore
from ..stores.pgvector_store import PgVectorStore
from ..stores.vector_base import SearchResult
from .rrf import reciprocal_rank_fusion

logger = logging.getLogger(__name__)


class HybridRetriever:
    """Retrieves documents from both PgVector and OpenSearch, merges with RRF."""

    def __init__(
        self,
        pgvector_store: PgVectorStore,
        opensearch_store: OpenSearchStore,
        embedding_model: EmbeddingModel,
        top_k: int = 10,
    ) -> None:
        self._pgvector = pgvector_store
        self._opensearch = opensearch_store
        self._embedder = embedding_model
        self._top_k = top_k

    def retrieve(
        self,
        query: str,
        top_k: int | None = None,
        filters: dict | None = None,
    ) -> list[SearchResult]:
        """Retrieve relevant documents for a query.

        Embeds the query, searches both stores, and merges with RRF.

        Args:
            query: Natural language query.
            top_k: Override default top_k.
            filters: Optional metadata filters.

        Returns:
            Merged and ranked list of SearchResult.
        """
        k = top_k or self._top_k

        query_embedding = self._embedder.embed([query])[0]

        pgvector_results: list[SearchResult] = []
        opensearch_results: list[SearchResult] = []

        try:
            pgvector_results = self._pgvector.search(
                query_embedding=query_embedding,
                top_k=k * 2,
                filters=filters,
            )
        except Exception as exc:
            logger.warning("PgVector search failed: %s", exc)

        try:
            opensearch_results = self._opensearch.search(
                query_embedding=query_embedding,
                top_k=k * 2,
                filters=filters,
            )
        except Exception as exc:
            logger.warning("OpenSearch search failed: %s", exc)

        if not pgvector_results and not opensearch_results:
            return []

        merged = reciprocal_rank_fusion([pgvector_results, opensearch_results])
        return merged[:k]
