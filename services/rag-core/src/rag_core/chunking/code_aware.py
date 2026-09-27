"""AST-aware chunker for Terraform HCL files."""

import logging
from typing import Any

from .base import Chunk, Chunker
from .recursive import RecursiveChunker

logger = logging.getLogger(__name__)


class TerraformHCLChunker(Chunker):
    """Splits Terraform HCL files at resource/module/variable boundaries.

    Uses python-hcl2 to parse the HCL AST and extract semantically
    complete blocks (resource, module, variable, output, data, locals).
    Falls back to recursive chunking on parse failure.
    """

    BLOCK_TYPES = ["resource", "module", "variable", "output", "data", "locals", "provider"]

    def __init__(self, chunk_size: int = 1024, chunk_overlap: int = 0) -> None:
        super().__init__(chunk_size, chunk_overlap)
        self._fallback = RecursiveChunker(chunk_size=chunk_size, chunk_overlap=64)

    def chunk(self, text: str, metadata: dict | None = None) -> list[Chunk]:
        """Chunk HCL content by block boundaries.

        Args:
            text: Terraform HCL content.
            metadata: Optional base metadata for all chunks.

        Returns:
            List of Chunk objects preserving semantic block boundaries.
        """
        if not text.strip():
            return []

        meta = metadata or {}

        try:
            return self._chunk_by_blocks(text, meta)
        except Exception as exc:
            logger.warning(
                "HCL parse failed, falling back to recursive chunking: %s", exc
            )
            return self._fallback.chunk(text, meta)

    def _chunk_by_blocks(self, text: str, metadata: dict) -> list[Chunk]:
        """Parse HCL and extract block-level chunks."""
        try:
            import hcl2  # type: ignore[import]
            import io

            parsed: dict[str, Any] = hcl2.load(io.StringIO(text))
        except ImportError:
            logger.warning("python-hcl2 not installed, using fallback chunking")
            return self._fallback.chunk(text, metadata)

        chunks: list[Chunk] = []
        lines = text.splitlines(keepends=True)

        for block_type in self.BLOCK_TYPES:
            if block_type not in parsed:
                continue

            blocks = parsed[block_type]
            if isinstance(blocks, dict):
                blocks = [blocks]

            for block in blocks:
                for block_name, block_content in block.items():
                    if isinstance(block_content, dict):
                        # resource "google_gcs_bucket" "my_bucket" { ... }
                        for resource_name, resource_body in block_content.items():
                            hcl_str = self._reconstruct_block(
                                block_type, block_name, resource_name, resource_body
                            )
                            block_meta = metadata.copy()
                            block_meta.update({
                                "block_type": block_type,
                                "block_name": block_name,
                                "resource_name": resource_name,
                                "resource_type": f"{block_type}.{block_name}.{resource_name}",
                            })
                            chunks.append(
                                Chunk(
                                    content=hcl_str,
                                    metadata=block_meta,
                                    token_count=self._count_tokens(hcl_str),
                                )
                            )
                    else:
                        # variable "my_var" { ... }
                        hcl_str = self._reconstruct_simple_block(
                            block_type, block_name, block_content
                        )
                        block_meta = metadata.copy()
                        block_meta.update({
                            "block_type": block_type,
                            "block_name": block_name,
                            "resource_type": f"{block_type}.{block_name}",
                        })
                        chunks.append(
                            Chunk(
                                content=hcl_str,
                                metadata=block_meta,
                                token_count=self._count_tokens(hcl_str),
                            )
                        )

        if not chunks:
            # HCL parsed but no recognized blocks — use fallback
            chunks = self._fallback.chunk(text, metadata)

        return chunks

    def _reconstruct_block(
        self,
        block_type: str,
        resource_type: str,
        resource_name: str,
        body: Any,
    ) -> str:
        """Reconstruct HCL block string from parsed dict."""
        lines = [f'{block_type} "{resource_type}" "{resource_name}" {{']
        lines.extend(self._dict_to_hcl(body, indent=2))
        lines.append("}")
        return "\n".join(lines)

    def _reconstruct_simple_block(
        self, block_type: str, block_name: str, body: Any
    ) -> str:
        """Reconstruct simple HCL block (variable, output, etc.)."""
        lines = [f'{block_type} "{block_name}" {{']
        lines.extend(self._dict_to_hcl(body, indent=2))
        lines.append("}")
        return "\n".join(lines)

    def _dict_to_hcl(self, obj: Any, indent: int = 0) -> list[str]:
        """Convert a dict to HCL-style lines."""
        lines: list[str] = []
        prefix = " " * indent

        if isinstance(obj, dict):
            for key, value in obj.items():
                if isinstance(value, dict):
                    lines.append(f"{prefix}{key} {{")
                    lines.extend(self._dict_to_hcl(value, indent + 2))
                    lines.append(f"{prefix}}}")
                elif isinstance(value, list):
                    for item in value:
                        if isinstance(item, dict):
                            lines.append(f"{prefix}{key} {{")
                            lines.extend(self._dict_to_hcl(item, indent + 2))
                            lines.append(f"{prefix}}}")
                        else:
                            lines.append(f"{prefix}{key} = {self._format_value(item)}")
                else:
                    lines.append(f"{prefix}{key} = {self._format_value(value)}")
        return lines

    def _format_value(self, value: Any) -> str:
        """Format a value for HCL output."""
        if isinstance(value, str):
            return f'"{value}"'
        if isinstance(value, bool):
            return str(value).lower()
        if value is None:
            return "null"
        return str(value)
