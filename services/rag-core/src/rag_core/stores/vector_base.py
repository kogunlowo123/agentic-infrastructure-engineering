"""Abstract vector store interface."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

import numpy as np


@dataclass
class SearchResult:
    """A search result from a vector store."""

    content: str
    metadata: dict = field(default_factory=dict)
    score: float = 0.0
    chunk_id: str = ""
    source: str = ""


class VectorStore(ABC):
    """Abstract vector store for embedding storage and retrieval."""

    @abstractmethod
    def upsert(
        self,
        chunk_ids: list[str],
        contents: list[str],
        embeddings: np.ndarray,
        metadatas: list[dict],
    ) -> None:
        """Insert or update document chunks with embeddings.

        Args:
            chunk_ids: Unique IDs for each chunk.
            contents: Text content of each chunk.
            embeddings: numpy array of shape (n, dim).
            metadatas: List of metadata dicts.
        """

    @abstractmethod
    def search(
        self,
        query_embedding: np.ndarray,
        top_k: int = 10,
        filters: dict | None = None,
    ) -> list[SearchResult]:
        """Search for similar documents.

        Args:
            query_embedding: Query embedding vector.
            top_k: Maximum results to return.
            filters: Optional metadata filter conditions.

        Returns:
            List of SearchResult ordered by relevance.
        """

    @abstractmethod
    def delete(self, chunk_ids: list[str]) -> None:
        """Delete chunks by ID."""

    @abstractmethod
    def count(self) -> int:
        """Return total document count in the store."""
