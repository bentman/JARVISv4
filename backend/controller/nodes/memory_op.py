"""
Node implementation for memory operations.
"""
from typing import Any, Dict
from .base import BaseNode
from ..engine.types import NodeType
from ...memory.schemas.memory import MemoryItem

class MemoryWriteNode(BaseNode):
    """
    A node that writes content to the memory store.
    """
    
    def __init__(self, id: str, description: str):
        super().__init__(id, NodeType.TOOL_CALL, description)

    async def execute(self, context: Any, results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the memory write operation.
        
        Expected context:
        - memory_store: The store instance (e.g., InMemoryStore)
        - content: str: The content to write
        - item_id: str: The ID to use for the memory item
        - metadata: dict (optional): Metadata for the memory item
        """
        store = context.get("memory_store")
        if not store:
            raise ValueError("memory_store not found in context")
            
        content = context.get("content")
        if not content:
            raise ValueError("content not found in context")
            
        item_id = context.get("item_id")
        if not item_id:
            raise ValueError("item_id not found in context")
            
        metadata = context.get("metadata", {})
        
        item = MemoryItem(
            id=item_id,
            content=content,
            metadata=metadata
        )
        
        store.put(item)
        
        return {
            "status": "success",
            "item_id": item_id
        }

class MemoryReadNode(BaseNode):
    """
    A node that reads content from the memory store.
    """
    
    def __init__(self, id: str, description: str):
        super().__init__(id, NodeType.TOOL_CALL, description)

    async def execute(self, context: Any, results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the memory read operation.
        
        Expected context:
        - memory_store: The store instance
        - item_id: str: The ID to read
        """
        store = context.get("memory_store")
        if not store:
            raise ValueError("memory_store not found in context")
            
        item_id = context.get("item_id")
        if not item_id:
            raise ValueError("item_id not found in context")
            
        item = store.get(item_id)
        if not item:
            return {
                "status": "not_found",
                "item_id": item_id
            }
            
        return {
            "status": "success",
            "item_id": item_id,
            "content": item.content,
            "metadata": item.metadata
        }
