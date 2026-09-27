"""HTML document loader using BeautifulSoup4."""

import logging
import re
from pathlib import Path

from .loader_registry import Document

logger = logging.getLogger(__name__)

# Tags that are typically not useful content
NOISE_TAGS = {"nav", "header", "footer", "aside", "script", "style", "noscript", "iframe"}


class HTMLLoader:
    """Loads and cleans text content from HTML files or URLs."""

    def load(self, path: str) -> Document:
        """Extract clean text from an HTML file.

        Args:
            path: Filesystem path to HTML file.

        Returns:
            Document with clean text and metadata.
        """
        from bs4 import BeautifulSoup  # type: ignore[import]

        html = Path(path).read_text(encoding="utf-8", errors="replace")
        return self._parse_html(html, source=path)

    def load_from_string(self, html: str, source: str = "") -> Document:
        """Parse HTML from a string."""
        return self._parse_html(html, source=source)

    def _parse_html(self, html: str, source: str = "") -> Document:
        from bs4 import BeautifulSoup  # type: ignore[import]

        soup = BeautifulSoup(html, "lxml")

        # Remove noise elements
        for tag in soup.find_all(NOISE_TAGS):
            tag.decompose()

        title = ""
        if soup.title and soup.title.string:
            title = soup.title.string.strip()

        # Extract text with structure preservation
        text_parts: list[str] = []
        for element in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "pre", "code"]):
            text = element.get_text(separator=" ", strip=True)
            if text:
                text_parts.append(text)

        full_text = "\n\n".join(text_parts)
        full_text = re.sub(r"\n{3,}", "\n\n", full_text)

        metadata = {
            "file_type": "html",
            "extension": ".html",
            "title": title,
            "source_path": source,
        }

        return Document(content=full_text, metadata=metadata, source=source)
