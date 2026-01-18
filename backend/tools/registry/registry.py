"""
Deterministic tool registry for JARVISv4.
Deriving minimal registry pattern from JARVISv3 MCPDispatcher.
"""
import logging
from typing import Dict, Any, List, Callable, Optional

logger = logging.getLogger(__name__)

class ToolRegistry:
    """
    Registry for managing and invoking deterministic tools.
    """

    def __init__(self):
        self._tools: Dict[str, Callable] = {}

    def register_tool(self, name: str, func: Callable):
        """Register a tool function with a given name."""
        self._tools[name] = func
        logger.info(f"Registered tool: {name}")

    def list_tools(self) -> List[str]:
        """List names of all registered tools."""
        return list(self._tools.keys())

    def get_tool(self, name: str) -> Optional[Callable]:
        """Retrieve a tool function by name."""
        return self._tools.get(name)

    async def call_tool(self, name: str, **kwargs) -> Any:
        """Invoke a registered tool with provided arguments."""
        tool_func = self.get_tool(name)
        if not tool_func:
            raise ValueError(f"Tool {name} not found in registry")

        logger.info(f"Calling tool: {name}")
        # Support both sync and async tool functions
        import asyncio
        if asyncio.iscoroutinefunction(tool_func):
            return await tool_func(**kwargs)
        else:
            return tool_func(**kwargs)
