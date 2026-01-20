"""
Deterministic tool registry for JARVISv4.
Manages tool discovery, metadata for LLMs, and schema-validated execution.
"""
import logging
from typing import Dict, Any, List, Optional
from jsonschema import validate, ValidationError

from backend.tools.base import BaseTool, ToolDefinition

logger = logging.getLogger(__name__)

class ToolRegistry:
    """
    Registry for managing and invoking deterministic tools.
    """

    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}

    def register_tool(self, tool: BaseTool):
        """Register a tool with its full definition."""
        name = tool.definition.name
        self._tools[name] = tool
        logger.info(f"Registered tool: {name}")

    def list_tools(self) -> List[str]:
        """List names of all registered tools."""
        return list(self._tools.keys())

    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """Return a list of tool definitions for LLM prompting."""
        return [
            {
                "name": t.definition.name,
                "description": t.definition.description,
                "parameters": t.definition.parameters
            }
            for t in self._tools.values()
        ]

    def get_tool(self, name: str) -> Optional[BaseTool]:
        """Retrieve a tool by name."""
        return self._tools.get(name)

    async def call_tool(self, name: str, **kwargs) -> Any:
        """
        Invoke a registered tool with provided arguments, 
        performing schema validation before execution.
        """
        tool = self.get_tool(name)
        if not tool:
            raise ValueError(f"Tool {name} not found in registry")

        # Validate arguments against tool's JSON Schema
        try:
            validate(instance=kwargs, schema=tool.definition.parameters)
        except ValidationError as e:
            logger.error(f"Validation error for tool {name}: {str(e)}")
            raise ValueError(f"Invalid parameters for tool {name}: {e.message}")

        logger.info(f"Calling tool: {name}")
        return await tool.execute(**kwargs)
