"""Agent planner — routes requests to the appropriate workflow graph."""

from __future__ import annotations

import logging
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class TaskType(str, Enum):
    IAC_GENERATION = "iac_generation"
    DRIFT_DETECTION = "drift_detection"
    COST_OPTIMIZATION = "cost_optimization"


class AgentPlanner:
    """Determines which agent graph to execute based on the task type."""

    def __init__(self) -> None:
        self._graphs: dict[TaskType, Any] = {}

    def _get_graph(self, task_type: TaskType) -> Any:
        """Lazily initialize graphs to avoid startup overhead."""
        if task_type not in self._graphs:
            from .graph import (
                create_cost_optimizer_graph,
                create_drift_detector_graph,
                create_iac_generator_graph,
            )

            creators = {
                TaskType.IAC_GENERATION: create_iac_generator_graph,
                TaskType.DRIFT_DETECTION: create_drift_detector_graph,
                TaskType.COST_OPTIMIZATION: create_cost_optimizer_graph,
            }
            self._graphs[task_type] = creators[task_type]()

        return self._graphs[task_type]

    def plan(self, task_type: str, input_data: dict) -> tuple[Any, dict]:
        """Select and configure a graph for the given task.

        Args:
            task_type: Task type string (iac_generation, drift_detection, cost_optimization).
            input_data: Input dict matching the graph's state schema.

        Returns:
            Tuple of (compiled_graph, validated_input).

        Raises:
            ValueError: If task_type is unknown or input_data is invalid.
        """
        try:
            task = TaskType(task_type)
        except ValueError as exc:
            raise ValueError(
                f"Unknown task type: {task_type!r}. "
                f"Valid types: {[t.value for t in TaskType]}"
            ) from exc

        graph = self._get_graph(task)
        validated = self._validate_input(task, input_data)
        return graph, validated

    def _validate_input(self, task: TaskType, data: dict) -> dict:
        """Validate and normalize input data for the given task."""
        if task == TaskType.IAC_GENERATION:
            if not data.get("requirements"):
                raise ValueError("requirements field required for iac_generation")
            reqs = data["requirements"]
            if not reqs.get("resource_type"):
                raise ValueError("requirements.resource_type is required")
            reqs.setdefault("cloud", "gcp")
            reqs.setdefault("environment", "dev")
            reqs.setdefault("config", {})

        elif task == TaskType.DRIFT_DETECTION:
            if not data.get("project_id"):
                raise ValueError("project_id required for drift_detection")

        elif task == TaskType.COST_OPTIMIZATION:
            if not data.get("project_id"):
                raise ValueError("project_id required for cost_optimization")
            data.setdefault("analysis_period_days", 30)
            data.setdefault("include_recommendations", True)

        return data
