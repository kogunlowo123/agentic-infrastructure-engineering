"""Semantic chunker using sentence embeddings for natural boundary detection."""

import logging
from typing import TYPE_CHECKING

import numpy as np

from .base import Chunk, Chunker

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class SemanticChunker(Chunker):
    """Chunks text by detecting semantic boundaries using embedding similarity.

    Splits text into sentences, embeds them, and groups semantically
    similar consecutive sentences into chunks.
    """

    def __init__(
        self,
        chunk_size: int = 512,
        chunk_overlap: int = 64,
        similarity_threshold: float = 0.8,
        model_name: str = "BAAI/bge-small-en-v1.5",
    ) -> None:
        super().__init__(chunk_size, chunk_overlap)
        self.similarity_threshold = similarity_threshold
        self.model_name = model_name
        self._model = None

    def _get_model(self) -> "SentenceTransformer":  # type: ignore[name-defined]
        if self._model is None:
            from sentence_transformers import SentenceTransformer  # type: ignore[import]
            self._model = SentenceTransformer(self.model_name)
        return self._model

    def chunk(self, text: str, metadata: dict | None = None) -> list[Chunk]:
        """Split text at semantic boundaries.

        Args:
            text: Text to split.
            metadata: Optional metadata for chunks.

        Returns:
            Semantically coherent chunks.
        """
        if not text.strip():
            return []

        meta = metadata or {}
        sentences = self._split_sentences(text)

        if len(sentences) <= 1:
            return [
                Chunk(
                    content=text,
                    metadata=meta.copy(),
                    token_count=self._count_tokens(text),
                )
            ]

        try:
            model = self._get_model()
            embeddings = model.encode(sentences, normalize_embeddings=True)
        except Exception as exc:
            logger.warning("Semantic chunking failed, using sentence-based split: %s", exc)
            return self._simple_sentence_chunks(sentences, meta)

        groups = self._group_by_similarity(sentences, embeddings)
        chunks = []
        current_pos = 0

        for group in groups:
            content = " ".join(group)
            start = text.find(group[0], current_pos)
            end = start + len(content)
            current_pos = start
            chunks.append(
                Chunk(
                    content=content,
                    metadata=meta.copy(),
                    start_index=start,
                    end_index=end,
                    token_count=self._count_tokens(content),
                )
            )

        return chunks

    def _split_sentences(self, text: str) -> list[str]:
        """Split text into sentences."""
        import re
        sentences = re.split(r"(?<=[.!?])\s+", text)
        return [s.strip() for s in sentences if s.strip()]

    def _group_by_similarity(
        self,
        sentences: list[str],
        embeddings: np.ndarray,
    ) -> list[list[str]]:
        """Group consecutive sentences by semantic similarity."""
        if len(sentences) == 0:
            return []

        groups: list[list[str]] = [[sentences[0]]]

        for i in range(1, len(sentences)):
            similarity = float(np.dot(embeddings[i - 1], embeddings[i]))
            current_group_text = " ".join(groups[-1])

            if (
                similarity >= self.similarity_threshold
                and self._count_tokens(current_group_text) < self.chunk_size
            ):
                groups[-1].append(sentences[i])
            else:
                groups.append([sentences[i]])

        return groups

    def _simple_sentence_chunks(
        self, sentences: list[str], metadata: dict
    ) -> list[Chunk]:
        """Fallback: group sentences up to chunk_size."""
        chunks = []
        current: list[str] = []
        current_len = 0

        for sentence in sentences:
            sentence_len = self._count_tokens(sentence)
            if current_len + sentence_len > self.chunk_size and current:
                content = " ".join(current)
                chunks.append(
                    Chunk(
                        content=content,
                        metadata=metadata.copy(),
                        token_count=self._count_tokens(content),
                    )
                )
                current = []
                current_len = 0
            current.append(sentence)
            current_len += sentence_len

        if current:
            content = " ".join(current)
            chunks.append(
                Chunk(
                    content=content,
                    metadata=metadata.copy(),
                    token_count=self._count_tokens(content),
                )
            )

        return chunks
