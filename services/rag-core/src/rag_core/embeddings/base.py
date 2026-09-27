"""Abstract embedding model interface."""

from abc import ABC, abstractmethod

import numpy as np


class EmbeddingModel(ABC):
    """Abstract base class for text embedding models."""

    @abstractmethod
    def embed(self, texts: list[str]) -> np.ndarray:
        """Embed a list of texts.

        Args:
            texts: List of text strings to embed.

        Returns:
            numpy array of shape (n, embedding_dim).
        """

    async def embed_async(self, texts: list[str]) -> np.ndarray:
        """Async embed a list of texts. Default delegates to sync."""
        return self.embed(texts)

    @property
    @abstractmethod
    def embedding_dim(self) -> int:
        """Return the embedding dimension."""

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return the model name identifier."""
