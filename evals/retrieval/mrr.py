"""Mean Reciprocal Rank (MRR) evaluation for RAG retrieval pipeline.

MRR measures the average reciprocal rank of the first relevant document
in the retrieved list.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RankedResult:
    query: str
    retrieved_ids: list[str]
    relevant_ids: set[str]


def reciprocal_rank(result: RankedResult) -> float:
    """Compute reciprocal rank for a single query.

    RR = 1/rank of first relevant document, or 0 if none found.
    """
    for rank, doc_id in enumerate(result.retrieved_ids, start=1):
        if doc_id in result.relevant_ids:
            return 1.0 / rank
    return 0.0


def mean_reciprocal_rank(results: list[RankedResult]) -> float:
    """Compute Mean Reciprocal Rank (MRR) across multiple queries."""
    if not results:
        return 0.0
    scores = [reciprocal_rank(r) for r in results]
    return sum(scores) / len(scores)


def evaluate_mrr(queries: list[dict], retrieve_fn, top_k: int = 10) -> dict[str, float]:
    """Run MRR evaluation.

    Args:
        queries: List of {"query": str, "relevant_ids": list[str]} dicts.
        retrieve_fn: Callable(query, top_k) -> list of chunk_ids.
        top_k: Number of results to retrieve per query.

    Returns:
        Dict with "mrr" key and score.
    """
    results: list[RankedResult] = []

    for item in queries:
        query = item["query"]
        relevant_ids = set(item.get("relevant_ids", []))
        retrieved = retrieve_fn(query, top_k)
        retrieved_ids = [r if isinstance(r, str) else r.get("chunk_id", "") for r in retrieved]
        results.append(RankedResult(
            query=query,
            retrieved_ids=retrieved_ids,
            relevant_ids=relevant_ids,
        ))

    return {"mrr": mean_reciprocal_rank(results)}
