"""Corrective RAG: post-retrieval relevance filtering."""

import logging

from ..stores.vector_base import SearchResult

logger = logging.getLogger(__name__)


class CorrectiveRAG:
    """Filters retrieved documents for relevance using an LLM judge.

    Addresses hallucination risk by discarding retrieved chunks that
    are not actually relevant to the query, even if they scored well.
    """

    RELEVANCE_PROMPT = """Assess whether the following document is relevant
to answering the query. Respond with only 'RELEVANT' or 'NOT_RELEVANT'.

Query: {query}

Document:
{content}"""

    def __init__(
        self,
        model: str = "vertex_ai/gemini-1.5-flash",
        relevance_threshold: float = 0.7,
        max_candidates: int = 20,
        use_llm_judge: bool = False,
    ) -> None:
        self._model = model
        self._relevance_threshold = relevance_threshold
        self._max_candidates = max_candidates
        self._use_llm_judge = use_llm_judge

    def filter(
        self,
        query: str,
        results: list[SearchResult],
    ) -> list[SearchResult]:
        """Filter results by relevance to query.

        Args:
            query: Original search query.
            results: Retrieved documents to filter.

        Returns:
            Filtered list of relevant documents.
        """
        if not results:
            return []

        # Score-based filtering (fast path)
        score_filtered = [r for r in results if r.score >= self._relevance_threshold]

        # If we have enough results after score filtering, return them
        if len(score_filtered) >= 3:
            return score_filtered[: self._max_candidates]

        # If LLM judging is enabled and we have too few results, expand with LLM check
        if self._use_llm_judge and results:
            return self._llm_filter(query, results)

        # Return all results if nothing passes threshold (avoid empty retrieval)
        return results[: self._max_candidates] if results else []

    def _llm_filter(
        self, query: str, candidates: list[SearchResult]
    ) -> list[SearchResult]:
        """Use LLM to judge relevance of each candidate."""
        try:
            import litellm  # type: ignore[import]
        except ImportError:
            return candidates

        relevant = []
        for candidate in candidates[: self._max_candidates]:
            try:
                response = litellm.completion(
                    model=self._model,
                    messages=[
                        {
                            "role": "user",
                            "content": self.RELEVANCE_PROMPT.format(
                                query=query,
                                content=candidate.content[:1000],
                            ),
                        }
                    ],
                    max_tokens=10,
                    temperature=0.0,
                )
                verdict = response.choices[0].message.content.strip().upper()
                if "RELEVANT" in verdict and "NOT_RELEVANT" not in verdict:
                    relevant.append(candidate)
            except Exception as exc:
                logger.warning("LLM relevance check failed: %s", exc)
                relevant.append(candidate)  # Include on error

        return relevant or candidates[:3]
