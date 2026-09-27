"""Base tool interface for agent tools."""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any


class ToolScope(str, Enum):
    """Tool permission scope levels."""

    READ_ONLY = "read_only"
    READ_WRITE = "read_write"
    DESTRUCTIVE = "destructive"


class BaseTool(ABC):
    """Abstract base class for all agent tools."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique tool name."""

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description of the tool's function."""

    @property
    def scope(self) -> ToolScope:
        """Default permission scope for this tool."""
        return ToolScope.READ_ONLY

    @abstractmethod
    def invoke(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Execute the tool with the given input.

        Args:
            input_data: Tool-specific input parameters.

        Returns:
            Tool output as a dict.

        Raises:
            ValueError: If input validation fails.
            RuntimeError: If the tool execution fails.
        """

    def __call__(self, **kwargs: Any) -> dict[str, Any]:
        return self.invoke(kwargs)
