"""Local BGE embedding model using sentence-transformers."""

import logging

import numpy as np

from .base import EmbeddingModel

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "BAAI/bge-large-en-v1.5"
EMBEDDING_DIM = 1024


class LocalBGEEmbedder(EmbeddingModel):
    """BGE embedder using sentence-transformers running locally.

    Uses BAAI/bge-large-en-v1.5 by default (1024-dimensional embeddings).
    """

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL,
        device: str = "cpu",
        batch_size: int = 32,
    ) -> None:
        self._model_name = model_name
        self._device = device
        self._batch_size = batch_size
        self._model = None

    def _get_model(self) -> "SentenceTransformer":  # type: ignore[name-defined]
        if self._model is None:
            from sentence_transformers import SentenceTransformer  # type: ignore[import]
            logger.info("Loading BGE model: %s on %s", self._model_name, self._device)
            self._model = SentenceTransformer(self._model_name, device=self._device)
        return self._model

    def embed(self, texts: list[str]) -> np.ndarray:
        """Embed texts using BGE model.

        Args:
            texts: List of texts to embed.

        Returns:
            L2-normalized numpy array of shape (n, 1024).
        """
        if not texts:
            return np.empty((0, EMBEDDING_DIM), dtype=np.float32)

        model = self._get_model()
        embeddings = model.encode(
            texts,
            batch_size=self._batch_size,
            normalize_embeddings=True,
            show_progress_bar=False,
            convert_to_numpy=True,
        )
        return np.array(embeddings, dtype=np.float32)

    @property
    def embedding_dim(self) -> int:
        return EMBEDDING_DIM

    @property
    def model_name(self) -> str:
        return self._model_name
