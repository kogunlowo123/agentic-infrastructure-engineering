"""Registry mapping file types to document loaders."""

import logging
from pathlib import Path
from typing import Callable

logger = logging.getLogger(__name__)


class Document:
    """Represents a loaded document."""

    def __init__(
        self,
        content: str,
        metadata: dict | None = None,
        source: str = "",
    ) -> None:
        self.content = content
        self.metadata = metadata or {}
        self.source = source


LoaderFn = Callable[[str], Document]


class LoaderRegistry:
    """Registry of document loaders by file extension and MIME type."""

    def __init__(self) -> None:
        self._loaders: dict[str, type] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        from .pdf_loader import PDFLoader
        from .html_loader import HTMLLoader

        self.register(".pdf", PDFLoader)
        self.register(".html", HTMLLoader)
        self.register(".htm", HTMLLoader)
        self.register(".tf", self._hcl_loader_class())
        self.register(".hcl", self._hcl_loader_class())
        self.register(".md", self._text_loader_class())
        self.register(".txt", self._text_loader_class())
        self.register(".json", self._text_loader_class())
        self.register(".yaml", self._text_loader_class())
        self.register(".yml", self._text_loader_class())

    def _hcl_loader_class(self) -> type:
        class HCLLoader:
            def load(self, path: str) -> Document:
                content = Path(path).read_text(encoding="utf-8")
                return Document(
                    content=content,
                    metadata={"file_type": "terraform", "extension": ".tf"},
                    source=path,
                )
        return HCLLoader

    def _text_loader_class(self) -> type:
        class TextLoader:
            def load(self, path: str) -> Document:
                content = Path(path).read_text(encoding="utf-8", errors="replace")
                suffix = Path(path).suffix
                return Document(
                    content=content,
                    metadata={"file_type": "text", "extension": suffix},
                    source=path,
                )
        return TextLoader

    def register(self, extension: str, loader_class: type) -> None:
        """Register a loader for a file extension."""
        self._loaders[extension.lower()] = loader_class

    def get_loader(self, path: str) -> type | None:
        """Get the loader class for a file path."""
        extension = Path(path).suffix.lower()
        return self._loaders.get(extension)

    def load(self, path: str) -> Document | None:
        """Load a document from path using the registered loader."""
        loader_class = self.get_loader(path)
        if loader_class is None:
            logger.warning("No loader registered for: %s", path)
            return None

        try:
            loader = loader_class()
            return loader.load(path)
        except Exception as exc:
            logger.error("Failed to load %s: %s", path, exc)
            return None
