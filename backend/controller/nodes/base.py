"""
Base node interface for JARVISv4.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict
from ..engine.types import NodeType

class BaseNode(ABC):
    """Abstract base class for all workflow nodes."""
    
    def __init__(self, id: str, node_type: NodeType, description: str):
        self.id = id
        self.type = node_type
        self.description = description

    @abstractmethod
    async def execute(self, context: Any, results: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the node logic."""
        pass
