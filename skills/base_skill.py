"""Abstract base class that every agent skill must implement."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseSkill(ABC):
    """Template ensuring consistent skill metadata and execution."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique skill identifier used as the tool name."""

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable explanation of what the skill does."""

    @property
    @abstractmethod
    def input_schema(self) -> Dict[str, Any]:
        """JSON Schema describing parameters accepted by execute()."""

    @abstractmethod
    def execute(self, **kwargs: Any) -> Dict[str, Any]:
        """Run skill logic; return dict with success flag and data or error."""

    def validate_inputs(self, **kwargs: Any) -> None:
        """Raise ValueError when required parameters are missing or invalid."""
        for key in self.input_schema.get("required", []):
            if key not in kwargs or kwargs[key] is None:
                raise ValueError(f"Missing required parameter: {key}")
        props = self.input_schema.get("properties", {})
        for key, value in kwargs.items():
            if key not in props:
                continue
            expected = props[key].get("type")
            if expected == "string" and not isinstance(value, str):
                raise ValueError(f"{key} must be a string")
            if expected == "array" and not isinstance(value, list):
                raise ValueError(f"{key} must be a list")
            if expected == "object" and not isinstance(value, dict):
                raise ValueError(f"{key} must be an object")

    def to_tool_definition(self) -> Dict[str, Any]:
        """Convert this skill into an Anthropic tool definition."""
        return {"name": self.name, "description": self.description, "input_schema": self.input_schema}

    def run(self, **kwargs: Any) -> Dict[str, Any]:
        """Validate inputs, execute, and catch errors."""
        try:
            self.validate_inputs(**kwargs)
            return self.execute(**kwargs)
        except Exception as exc:
            return {"success": False, "error": str(exc)}
