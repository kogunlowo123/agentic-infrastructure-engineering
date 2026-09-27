"""Faithfulness evaluation for generated IaC.

Measures whether the generated HCL faithfully uses only resources/attributes
that appear in the retrieved context (no hallucinated resource types or
unsupported attributes).
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class FaithfulnessResult:
    query_id: str
    generated_hcl: str
    context_chunks: list[str]
    faithfulness_score: float
    hallucinated_resources: list[str]
    supported_resources: list[str]


def extract_resource_types(hcl: str) -> set[str]:
    """Extract resource type names from HCL text."""
    pattern = r'resource\s+"([^"]+)"\s+"[^"]+"'
    return set(re.findall(pattern, hcl))


def check_faithfulness(
    generated_hcl: str,
    context_chunks: list[str],
    query_id: str = "",
) -> FaithfulnessResult:
    """Check whether generated HCL uses only resource types found in context.

    A resource type is "supported" if it appears in at least one context chunk.
    A resource type is "hallucinated" if it appears in the HCL but not in any
    context chunk.

    Args:
        generated_hcl: The generated Terraform HCL string.
        context_chunks: Retrieved context chunks used for generation.
        query_id: Optional identifier for the query.

    Returns:
        FaithfulnessResult with score and lists of supported/hallucinated resources.
    """
    generated_types = extract_resource_types(generated_hcl)

    context_text = "\n".join(context_chunks)
    supported: list[str] = []
    hallucinated: list[str] = []

    for resource_type in generated_types:
        if resource_type in context_text:
            supported.append(resource_type)
        else:
            hallucinated.append(resource_type)

    total = len(generated_types)
    score = len(supported) / total if total > 0 else 1.0

    return FaithfulnessResult(
        query_id=query_id,
        generated_hcl=generated_hcl,
        context_chunks=context_chunks,
        faithfulness_score=score,
        hallucinated_resources=hallucinated,
        supported_resources=supported,
    )


def evaluate_faithfulness(
    examples: list[dict],
) -> dict[str, float]:
    """Evaluate faithfulness across a dataset.

    Args:
        examples: List of {"id", "generated_hcl", "context_chunks"} dicts.

    Returns:
        Dict with "mean_faithfulness" and "hallucination_rate" metrics.
    """
    if not examples:
        return {"mean_faithfulness": 0.0, "hallucination_rate": 0.0}

    scores = []
    hallucination_counts = 0
    total_resources = 0

    for ex in examples:
        result = check_faithfulness(
            generated_hcl=ex["generated_hcl"],
            context_chunks=ex.get("context_chunks", []),
            query_id=ex.get("id", ""),
        )
        scores.append(result.faithfulness_score)
        hallucination_counts += len(result.hallucinated_resources)
        total_resources += len(result.supported_resources) + len(result.hallucinated_resources)

    mean_faithfulness = sum(scores) / len(scores)
    hallucination_rate = hallucination_counts / total_resources if total_resources > 0 else 0.0

    return {
        "mean_faithfulness": mean_faithfulness,
        "hallucination_rate": hallucination_rate,
    }
