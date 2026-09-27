"""Reciprocal Rank Fusion for merging multiple ranked lists."""

from ..stores.vector_base import SearchResult


def reciprocal_rank_fusion(
    results_lists: list[list[SearchResult]],
    k: int = 60,
) -> list[SearchResult]:
    """Merge multiple ranked result lists using Reciprocal Rank Fusion.

    RRF score = sum(1 / (k + rank_i)) for each result list i.

    Args:
        results_lists: List of ranked result lists to merge.
        k: Constant to prevent large scores for top-ranked items (default 60).

    Returns:
        Merged and re-ranked list of SearchResult, deduplicated by chunk_id.
    """
    scores: dict[str, float] = {}
    best_results: dict[str, SearchResult] = {}

    for result_list in results_lists:
        for rank, result in enumerate(result_list, start=1):
            key = result.chunk_id or result.content[:64]
            rrf_score = 1.0 / (k + rank)
            scores[key] = scores.get(key, 0.0) + rrf_score
            if key not in best_results or result.score > best_results[key].score:
                best_results[key] = result

    merged = []
    for key, total_score in sorted(scores.items(), key=lambda x: x[1], reverse=True):
        result = best_results[key]
        merged.append(
            SearchResult(
                content=result.content,
                metadata=result.metadata,
                score=total_score,
                chunk_id=result.chunk_id,
                source=result.source,
            )
        )

    return merged
