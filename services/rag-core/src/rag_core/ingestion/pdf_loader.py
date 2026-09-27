"""PDF document loader using PyPDF2."""

import logging
from pathlib import Path

from .loader_registry import Document

logger = logging.getLogger(__name__)


class PDFLoader:
    """Loads text content from PDF files."""

    def load(self, path: str) -> Document:
        """Extract text and metadata from a PDF file.

        Args:
            path: Filesystem path to the PDF file.

        Returns:
            Document with extracted text and metadata.
        """
        try:
            from pypdf import PdfReader  # type: ignore[import]
        except ImportError:
            from PyPDF2 import PdfReader  # type: ignore[import]

        reader = PdfReader(path)
        pages: list[str] = []

        for page in reader.pages:
            text = page.extract_text()
            if text:
                pages.append(text)

        full_text = "\n\n".join(pages)

        info = reader.metadata or {}
        metadata = {
            "file_type": "pdf",
            "extension": ".pdf",
            "page_count": len(reader.pages),
            "title": str(info.get("/Title", "")),
            "author": str(info.get("/Author", "")),
            "source_path": path,
        }

        return Document(content=full_text, metadata=metadata, source=path)
