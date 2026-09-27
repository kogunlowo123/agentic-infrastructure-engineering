"""Recursive character text splitter for general documents."""

from .base import Chunk, Chunker


class RecursiveChunker(Chunker):
    """Splits text recursively by separator hierarchy."""

    DEFAULT_SEPARATORS = ["\n\n", "\n", ". ", " ", ""]

    def __init__(
        self,
        chunk_size: int = 512,
        chunk_overlap: int = 64,
        separators: list[str] | None = None,
    ) -> None:
        super().__init__(chunk_size, chunk_overlap)
        self.separators = separators or self.DEFAULT_SEPARATORS

    def chunk(self, text: str, metadata: dict | None = None) -> list[Chunk]:
        """Split text into chunks using recursive separator strategy.

        Args:
            text: The text to split.
            metadata: Optional metadata for all chunks.

        Returns:
            List of Chunk objects.
        """
        if not text.strip():
            return []

        meta = metadata or {}
        raw_chunks = self._split(text, self.separators)
        chunks = []
        offset = 0

        for raw in raw_chunks:
            start = text.find(raw, offset)
            end = start + len(raw)
            offset = max(0, end - self.chunk_overlap)
            chunks.append(
                Chunk(
                    content=raw,
                    metadata=meta.copy(),
                    start_index=start,
                    end_index=end,
                    token_count=self._count_tokens(raw),
                )
            )

        return chunks

    def _split(self, text: str, separators: list[str]) -> list[str]:
        """Recursively split text by separator list."""
        if not separators:
            return [text]

        separator = separators[0]
        remaining = separators[1:]

        if not separator:
            # Character-level split
            words = list(text)
            return self._merge_splits(words, "")

        parts = text.split(separator)
        good_parts: list[str] = []
        pending = ""

        for part in parts:
            candidate = (pending + separator + part).strip() if pending else part.strip()
            if self._count_tokens(candidate) <= self.chunk_size:
                pending = candidate
            else:
                if pending:
                    good_parts.append(pending)
                if self._count_tokens(part) > self.chunk_size:
                    good_parts.extend(self._split(part, remaining))
                    pending = ""
                else:
                    pending = part

        if pending:
            good_parts.append(pending)

        return [p for p in good_parts if p.strip()]

    def _merge_splits(self, splits: list[str], separator: str) -> list[str]:
        """Merge small splits back into chunks of the desired size."""
        chunks: list[str] = []
        current: list[str] = []
        current_len = 0

        for split in splits:
            split_len = self._count_tokens(split)
            if current_len + split_len > self.chunk_size:
                if current:
                    chunks.append(separator.join(current))
                    # Keep overlap
                    while current and current_len > self.chunk_overlap:
                        current_len -= self._count_tokens(current.pop(0))
                current.append(split)
                current_len += split_len
            else:
                current.append(split)
                current_len += split_len

        if current:
            chunks.append(separator.join(current))

        return chunks
