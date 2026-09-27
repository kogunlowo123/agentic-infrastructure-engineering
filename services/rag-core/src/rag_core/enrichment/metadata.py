"""Metadata extraction for ingested documents."""

import hashlib
import os
from pathlib import Path


class MetadataExtractor:
    """Extracts standard metadata fields from documents."""

    def extract(self, content: str, source: str = "") -> dict:
        """Extract metadata from document content and source path.

        Args:
            content: Document text content.
            source: Source file path or URL.

        Returns:
            Metadata dict with standard fields.
        """
        path = Path(source) if source else None
        return {
            "doc_type": self._detect_doc_type(content, source),
            "source_url": source,
            "file_extension": path.suffix.lower() if path else "",
            "size_bytes": len(content.encode("utf-8")),
            "checksum": hashlib.sha256(content.encode()).hexdigest(),
            "char_count": len(content),
            "line_count": content.count("\n"),
        }

    def _detect_doc_type(self, content: str, source: str) -> str:
        """Heuristically detect document type."""
        source_lower = source.lower()
        if source_lower.endswith((".tf", ".hcl")):
            return "terraform"
        if "resource" in content and "provider" in content:
            return "terraform"
        if source_lower.endswith(".md"):
            return "documentation"
        if source_lower.endswith((".yaml", ".yml")):
            return "configuration"
        return "text"
