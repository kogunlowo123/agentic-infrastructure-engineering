"""Cross-encoder reranker for improving retrieval precision."""

import logging
from typing import Any

from ..stores.vector_base import SearchResult

logger = logging.getLogger(__name__)


class CrossEncoderReranker:
    """Reranks search results using a cross-encoder model.

    Uses ms-marco-MiniLM cross-encoder for high-precision reranking
    of top candidate documents.
    """

    DEFAULT_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL,
        top_k: int = 3,
        device: str = "cpu",
    ) -> None:
        self._model_name = model_name
        self._top_k = top_k
        self._device = device
        self._model: Any = None

    def _get_model(self) -> Any:
        if self._model is None:
            from sentence_transformers import CrossEncoder  # type: ignore[import]
            logger.info("Loading cross-encoder: %s", self._model_name)
            self._model = CrossEncoder(self._model_name, device=self._device)
        return self._model

    def rerank(
        self,
        query: str,
        candidates: list[SearchResult],
        top_k: int | None = None,
    ) -> list[SearchResult]:
        """Rerank candidates using cross-encoder relevance scores.

        Args:
            query: Original query string.
            candidates: Candidate search results to rerank.
            top_k: Number of results to return after reranking.

        Returns:
            Reranked list of SearchResult with updated scores.
        """
        if not candidates:
            return []

        k = top_k or self._top_k

        try:
            model = self._get_model()
            pairs = [(query, c.content) for c in candidates]
            scores = model.predict(pairs)
        except Exception as exc:
            logger.warning("Reranking failed, returning original order: %s", exc)
            return candidates[:k]

        scored = list(zip(candidates, scores))
        scored.sort(key=lambda x: x[1], reverse=True)

        results = []
        for result, score in scored[:k]:
            results.append(
                SearchResult(
                    content=result.content,
                    metadata=result.metadata,
                    score=float(score),
                    chunk_id=result.chunk_id,
                    source=result.source,
                )
            )

        return results
