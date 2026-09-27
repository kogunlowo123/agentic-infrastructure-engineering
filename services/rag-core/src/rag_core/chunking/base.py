"""Base chunking interface for RAG document processing."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class Chunk:
    """A chunk of text with associated metadata."""

    content: str
    metadata: dict = field(default_factory=dict)
    start_index: int = 0
    end_index: int = 0
    token_count: int = 0
    chunk_id: str = ""

    def __post_init__(self) -> None:
        if not self.chunk_id:
            import hashlib
            self.chunk_id = hashlib.md5(
                (self.content + str(self.start_index)).encode()
            ).hexdigest()


class Chunker(ABC):
    """Abstract base class for text chunkers."""

    def __init__(self, chunk_size: int = 512, chunk_overlap: int = 64) -> None:
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    @abstractmethod
    def chunk(self, text: str, metadata: dict | None = None) -> list[Chunk]:
        """Split text into chunks.

        Args:
            text: The text to chunk.
            metadata: Optional metadata to attach to all chunks.

        Returns:
            List of Chunk objects.
        """

    def _count_tokens(self, text: str) -> int:
        """Approximate token count using whitespace splitting."""
        return len(text.split())
