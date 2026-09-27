"""Query rewriting for improved retrieval coverage."""

import logging

logger = logging.getLogger(__name__)


class QueryRewriter:
    """Expands and rewrites queries for better retrieval recall.

    Uses an LLM to generate query variants that improve coverage
    of relevant documents in the vector store.
    """

    REWRITE_PROMPT = """You are a search query optimizer for Terraform IaC documentation.
Given a user query, generate {n} alternative search queries that would retrieve
relevant Terraform resources, modules, or configuration patterns.

Original query: {query}

Return only the alternative queries, one per line, without numbering or explanation."""

    def __init__(
        self,
        model: str = "vertex_ai/gemini-1.5-flash",
        n_rewrites: int = 3,
    ) -> None:
        self._model = model
        self._n_rewrites = n_rewrites

    def rewrite(self, query: str) -> list[str]:
        """Generate alternative query formulations.

        Args:
            query: Original search query.

        Returns:
            List of alternative queries including the original.
        """
        try:
            import litellm  # type: ignore[import]

            response = litellm.completion(
                model=self._model,
                messages=[
                    {
                        "role": "user",
                        "content": self.REWRITE_PROMPT.format(
                            query=query,
                            n=self._n_rewrites,
                        ),
                    }
                ],
                max_tokens=512,
                temperature=0.3,
            )

            alternatives_text = response.choices[0].message.content.strip()
            alternatives = [
                line.strip()
                for line in alternatives_text.split("\n")
                if line.strip()
            ]
            return [query] + alternatives[: self._n_rewrites]

        except Exception as exc:
            logger.warning("Query rewriting failed: %s", exc)
            return [query]
