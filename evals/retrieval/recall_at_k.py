"""Recall@K evaluation for RAG retrieval pipeline.

Measures the fraction of relevant documents retrieved in the top-K results.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class RetrievalResult:
    query: str
    retrieved_ids: list[str]
    relevant_ids: set[str]


def recall_at_k(result: RetrievalResult, k: int) -> float:
    """Compute Recall@K for a single query.

    Recall@K = |relevant ∩ top-K retrieved| / |relevant|

    Args:
        result: Retrieved and relevant document IDs for a query.
        k: Number of top retrieved documents to consider.

    Returns:
        Recall score in [0.0, 1.0].
    """
    if not result.relevant_ids:
        return 1.0  # No relevant docs — vacuously correct

    top_k = set(result.retrieved_ids[:k])
    hits = top_k & result.relevant_ids
    return len(hits) / len(result.relevant_ids)


def mean_recall_at_k(results: list[RetrievalResult], k: int) -> float:
    """Compute mean Recall@K across multiple queries."""
    if not results:
        return 0.0
    scores = [recall_at_k(r, k) for r in results]
    return sum(scores) / len(scores)


def evaluate_retrieval(
    queries: list[dict[str, Any]],
    retrieve_fn: Any,
    k_values: list[int] = None,
) -> dict[str, float]:
    """Run Recall@K evaluation for multiple K values.

    Args:
        queries: List of {"query": str, "relevant_ids": list[str]} dicts.
        retrieve_fn: Callable(query, top_k) -> list of chunk_ids.
        k_values: K values to evaluate (default: [1, 3, 5, 10]).

    Returns:
        Dict mapping "recall@K" to score.
    """
    if k_values is None:
        k_values = [1, 3, 5, 10]

    max_k = max(k_values)
    results: list[RetrievalResult] = []

    for item in queries:
        query = item["query"]
        relevant_ids = set(item.get("relevant_ids", []))
        retrieved = retrieve_fn(query, max_k)
        results.append(RetrievalResult(
            query=query,
            retrieved_ids=[r if isinstance(r, str) else r.get("chunk_id", "") for r in retrieved],
            relevant_ids=relevant_ids,
        ))

    metrics: dict[str, float] = {}
    for k in k_values:
        metrics[f"recall@{k}"] = mean_recall_at_k(results, k)

    return metrics
