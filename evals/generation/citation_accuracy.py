"""Citation accuracy evaluation for generated IaC.

Measures whether the generated HCL cites (references) the correct source
chunks from the retrieval context.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CitationResult:
    query_id: str
    precision: float
    recall: float
    f1: float


def citation_accuracy(
    cited_chunk_ids: list[str],
    relevant_chunk_ids: set[str],
    query_id: str = "",
) -> CitationResult:
    """Compute citation precision, recall, and F1.

    Args:
        cited_chunk_ids: Chunk IDs the model cited in its output.
        relevant_chunk_ids: Ground-truth relevant chunk IDs.
        query_id: Optional query identifier.

    Returns:
        CitationResult with precision, recall, F1.
    """
    cited = set(cited_chunk_ids)
    relevant = set(relevant_chunk_ids)

    true_positives = len(cited & relevant)
    precision = true_positives / len(cited) if cited else 0.0
    recall = true_positives / len(relevant) if relevant else 1.0

    if precision + recall > 0:
        f1 = 2 * precision * recall / (precision + recall)
    else:
        f1 = 0.0

    return CitationResult(
        query_id=query_id,
        precision=precision,
        recall=recall,
        f1=f1,
    )


def evaluate_citation_accuracy(examples: list[dict]) -> dict[str, float]:
    """Evaluate citation accuracy across a dataset.

    Args:
        examples: List of dicts with:
            - "id": query identifier
            - "cited_chunk_ids": list of chunk IDs cited by the model
            - "relevant_chunk_ids": list of ground-truth relevant chunk IDs

    Returns:
        Dict with mean_precision, mean_recall, mean_f1.
    """
    if not examples:
        return {"mean_precision": 0.0, "mean_recall": 0.0, "mean_f1": 0.0}

    results = [
        citation_accuracy(
            cited_chunk_ids=ex.get("cited_chunk_ids", []),
            relevant_chunk_ids=set(ex.get("relevant_chunk_ids", [])),
            query_id=ex.get("id", ""),
        )
        for ex in examples
    ]

    n = len(results)
    return {
        "mean_precision": sum(r.precision for r in results) / n,
        "mean_recall": sum(r.recall for r in results) / n,
        "mean_f1": sum(r.f1 for r in results) / n,
    }
