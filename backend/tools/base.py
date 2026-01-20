from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from dataclasses import dataclass

@dataclass(frozen=True)
class ToolDefinition:
    """Structure for tool metadata used by LLMs and validation."""
    name: str
    description: str
    parameters: Dict[str, Any]  # JSON Schema

class BaseTool(ABC):
    """Abstract base class for all JARVISv4 tools."""
    
    @property
    @abstractmethod
    def definition(self) -> ToolDefinition:
        """Return the tool's metadata definition."""
        pass

    @abstractmethod
    async def execute(self, **kwargs) -> Any:
        """
        Implementation of the tool's logic.
        
        Args:
            **kwargs: Arguments following the tool's parameter schema.
            
        Returns:
            The result of tool execution.
        """
        pass
