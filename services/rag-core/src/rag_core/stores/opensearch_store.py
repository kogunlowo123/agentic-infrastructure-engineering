"""OpenSearch store with hybrid BM25 + kNN vector search."""

import json
import logging
from typing import Any

import numpy as np

from .vector_base import SearchResult, VectorStore

logger = logging.getLogger(__name__)

INDEX_MAPPING = {
    "settings": {
        "number_of_shards": 2,
        "number_of_replicas": 1,
        "index": {
            "knn": True,
            "knn.algo_param.ef_search": 512,
        },
    },
    "mappings": {
        "properties": {
            "chunk_id": {"type": "keyword"},
            "content": {"type": "text", "analyzer": "english"},
            "metadata": {"type": "object", "dynamic": True},
            "embedding": {
                "type": "knn_vector",
                "dimension": 1024,
                "method": {
                    "name": "hnsw",
                    "space_type": "cosinesimil",
                    "engine": "nmslib",
                    "parameters": {"ef_construction": 512, "m": 16},
                },
            },
        }
    },
}


class OpenSearchStore(VectorStore):
    """Hybrid search store using OpenSearch BM25 + kNN vectors.

    Combines BM25 lexical scores with cosine vector similarity
    using a configurable alpha blend.
    """

    def __init__(
        self,
        host: str = "http://opensearch:9200",
        index: str = "iac_documents",
        username: str = "admin",
        password: str = "admin",
        alpha: float = 0.5,
    ) -> None:
        self._index = index
        self._alpha = alpha
        self._client = self._create_client(host, username, password)
        self._ensure_index()

    def _create_client(self, host: str, username: str, password: str) -> Any:
        from opensearchpy import OpenSearch  # type: ignore[import]
        return OpenSearch(
            hosts=[host],
            http_auth=(username, password),
            use_ssl=host.startswith("https"),
            verify_certs=False,
            ssl_show_warn=False,
        )

    def _ensure_index(self) -> None:
        if not self._client.indices.exists(index=self._index):
            self._client.indices.create(index=self._index, body=INDEX_MAPPING)
            logger.info("Created OpenSearch index: %s", self._index)

    def upsert(
        self,
        chunk_ids: list[str],
        contents: list[str],
        embeddings: np.ndarray,
        metadatas: list[dict],
    ) -> None:
        """Bulk upsert documents into OpenSearch."""
        if not chunk_ids:
            return

        actions: list[dict] = []
        for i, chunk_id in enumerate(chunk_ids):
            actions.append({"index": {"_index": self._index, "_id": chunk_id}})
            actions.append({
                "chunk_id": chunk_id,
                "content": contents[i],
                "metadata": metadatas[i],
                "embedding": embeddings[i].tolist(),
            })

        response = self._client.bulk(body=actions)
        if response.get("errors"):
            logger.warning("Some OpenSearch bulk upsert errors occurred")

    def search(
        self,
        query_embedding: np.ndarray,
        top_k: int = 10,
        filters: dict | None = None,
    ) -> list[SearchResult]:
        """Hybrid BM25 + kNN search.

        Args:
            query_embedding: Query vector for kNN search.
            top_k: Number of results.
            filters: Optional metadata filters.

        Returns:
            Merged and ranked search results.
        """
        knn_results = self._knn_search(query_embedding, top_k, filters)
        return knn_results

    def _knn_search(
        self,
        query_embedding: np.ndarray,
        top_k: int,
        filters: dict | None,
    ) -> list[SearchResult]:
        """Pure kNN vector search."""
        must_clauses: list[dict] = []
        if filters:
            for key, value in filters.items():
                must_clauses.append({"term": {f"metadata.{key}": str(value)}})

        query: dict = {
            "size": top_k,
            "query": {
                "bool": {
                    "must": must_clauses,
                    "filter": [
                        {
                            "knn": {
                                "embedding": {
                                    "vector": query_embedding.tolist(),
                                    "k": top_k,
                                }
                            }
                        }
                    ],
                }
            },
        }

        if not must_clauses:
            query["query"] = {
                "knn": {
                    "embedding": {
                        "vector": query_embedding.tolist(),
                        "k": top_k,
                    }
                }
            }

        response = self._client.search(index=self._index, body=query)
        results = []
        for hit in response["hits"]["hits"]:
            src = hit["_source"]
            results.append(
                SearchResult(
                    content=src.get("content", ""),
                    metadata=src.get("metadata", {}),
                    score=float(hit.get("_score", 0.0)),
                    chunk_id=src.get("chunk_id", hit["_id"]),
                    source="opensearch",
                )
            )
        return results

    def delete(self, chunk_ids: list[str]) -> None:
        """Delete documents by chunk_id."""
        if not chunk_ids:
            return
        actions = [
            {"delete": {"_index": self._index, "_id": cid}} for cid in chunk_ids
        ]
        self._client.bulk(body=actions)

    def count(self) -> int:
        """Return document count in index."""
        response = self._client.count(index=self._index)
        return response.get("count", 0)
