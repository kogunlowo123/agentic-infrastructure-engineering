"""RAG search tool for retrieving Terraform templates and documentation."""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx

from .base import BaseTool, ToolScope

logger = logging.getLogger(__name__)


class RAGSearchTool(BaseTool):
    """Searches the RAG corpus for relevant Terraform templates and documentation."""

    def __init__(
        self,
        rag_core_url: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        self._rag_url = rag_core_url or os.getenv("RAG_CORE_URL", "http://rag-core:8082")
        self._timeout = timeout

    @property
    def name(self) -> str:
        return "rag_search"

    @property
    def description(self) -> str:
        return (
            "Search the Terraform IaC knowledge base for relevant templates, "
            "resource configurations, and infrastructure patterns."
        )

    @property
    def scope(self) -> ToolScope:
        return ToolScope.READ_ONLY

    def invoke(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Search RAG corpus for relevant documents.

        Args:
            input_data: {
                query (str): Search query,
                top_k (int): Number of results (default 10),
                doc_types (list[str]): Filter by document type,
                resource_types (list[str]): Filter by Terraform resource type,
            }

        Returns:
            {results: list[{content, metadata, score, chunk_id}]}
        """
        query = input_data.get("query", "")
        if not query:
            raise ValueError("query is required")

        top_k = int(input_data.get("top_k", 10))
        filters: dict[str, Any] = {}

        if doc_types := input_data.get("doc_types"):
            filters["file_type"] = doc_types[0] if isinstance(doc_types, list) else doc_types

        if resource_types := input_data.get("resource_types"):
            filters["resource_type"] = (
                resource_types[0] if isinstance(resource_types, list) else resource_types
            )

        payload = {"query": query, "top_k": top_k}
        if filters:
            payload["filters"] = filters

        try:
            response = httpx.post(
                f"{self._rag_url}/retrieve",
                json=payload,
                timeout=self._timeout,
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as exc:
            logger.error("RAG search request failed: %s", exc)
            return {"results": [], "error": str(exc)}
        except Exception as exc:
            logger.error("RAG search failed: %s", exc)
            return {"results": [], "error": str(exc)}
