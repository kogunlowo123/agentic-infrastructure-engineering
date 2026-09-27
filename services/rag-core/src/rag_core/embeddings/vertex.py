"""Vertex AI embedding model using LiteLLM."""

import asyncio
import logging
import time
from typing import Any

import numpy as np

from .base import EmbeddingModel

logger = logging.getLogger(__name__)

VERTEX_MODEL = "vertex_ai/text-embedding-004"
VERTEX_DIM = 768


class VertexAIEmbedder(EmbeddingModel):
    """Text embeddings via Vertex AI using LiteLLM.

    Supports async embedding with exponential backoff for rate limits.
    """

    def __init__(
        self,
        model: str = VERTEX_MODEL,
        project_id: str = "",
        location: str = "us-central1",
        max_retries: int = 3,
        batch_size: int = 32,
    ) -> None:
        self._model = model
        self._project_id = project_id
        self._location = location
        self._max_retries = max_retries
        self._batch_size = batch_size

    def embed(self, texts: list[str]) -> np.ndarray:
        """Embed synchronously by running the async version."""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(self.embed_async(texts))

    async def embed_async(self, texts: list[str]) -> np.ndarray:
        """Embed texts asynchronously using Vertex AI.

        Args:
            texts: List of texts to embed.

        Returns:
            numpy array of shape (n, 768).
        """
        if not texts:
            return np.empty((0, VERTEX_DIM), dtype=np.float32)

        all_embeddings: list[list[float]] = []

        for i in range(0, len(texts), self._batch_size):
            batch = texts[i : i + self._batch_size]
            embeddings = await self._embed_batch_with_retry(batch)
            all_embeddings.extend(embeddings)

        return np.array(all_embeddings, dtype=np.float32)

    async def _embed_batch_with_retry(
        self, texts: list[str]
    ) -> list[list[float]]:
        """Embed a batch with exponential backoff retry."""
        import litellm  # type: ignore[import]

        last_error: Exception | None = None

        for attempt in range(self._max_retries):
            try:
                response = await litellm.aembedding(
                    model=self._model,
                    input=texts,
                )
                return [item["embedding"] for item in response.data]
            except Exception as exc:
                last_error = exc
                wait_time = 2 ** attempt
                logger.warning(
                    "Vertex AI embedding attempt %d failed: %s. Retrying in %ds",
                    attempt + 1,
                    exc,
                    wait_time,
                )
                await asyncio.sleep(wait_time)

        raise RuntimeError(
            f"Vertex AI embedding failed after {self._max_retries} attempts"
        ) from last_error

    @property
    def embedding_dim(self) -> int:
        return VERTEX_DIM

    @property
    def model_name(self) -> str:
        return self._model
