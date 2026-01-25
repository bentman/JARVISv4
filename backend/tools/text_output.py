"""
Deterministic text output tool for JARVISv4.
Returns caller-provided text verbatim with no side effects.
"""
from typing import Any

from backend.tools.base import BaseTool, ToolDefinition


class TextOutputTool(BaseTool):
    """Return the provided text verbatim."""

    def __init__(self):
        self._definition = ToolDefinition(
            name="text_output",
            description="Return the provided text verbatim (deterministic; no side effects).",
            parameters={
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "Text to return verbatim."
                    }
                },
                "required": ["text"],
                "additionalProperties": False
            }
        )

    @property
    def definition(self) -> ToolDefinition:
        return self._definition

    async def execute(self, **kwargs) -> Any:
        return kwargs["text"]