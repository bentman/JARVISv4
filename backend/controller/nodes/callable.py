"""
Node implementation that executes a provided callable.
"""
from typing import Any, Dict, Callable
from .base import BaseNode
from ..engine.types import NodeType

class CallableNode(BaseNode):
    """
    A node that executes a provided Python function.
    """
    
    def __init__(self, id: str, node_type: NodeType, description: str, func: Callable):
        super().__init__(id, node_type, description)
        self.func = func

    async def execute(self, context: Any, results: Dict[str, Any]) -> Dict[str, Any]:
        """Invoke the stored callable."""
        import asyncio
        if asyncio.iscoroutinefunction(self.func):
            return await self.func(context, results)
        else:
            return self.func(context, results)
