"""
Node implementation for memory operations.
"""
from typing import Any, Dict
from .base import BaseNode
from ..engine.types import NodeType, TaskContext
from ...memory.schemas.memory import MemoryItem

class MemoryWriteNode(BaseNode):
    """
    A node that writes content to the memory store.
    """
    
    def __init__(self, id: str, description: str):
        super().__init__(id, NodeType.TOOL_CALL, description)

    async def execute(self, context: TaskContext, results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the memory write operation.
        
        Expected context:
        - memory_store: The store instance (e.g., InMemoryStore)
        - data['content']: str: The content to write
        - data['item_id']: str: The ID to use for the memory item
        - data['metadata']: dict (optional): Metadata for the memory item
        """
        store = context.memory_store
        if not store:
            raise ValueError("memory_store not found in context")
            
        content = context.data.get("content")
        if not content:
            raise ValueError("content not found in context.data")
            
        item_id = context.data.get("item_id")
        if not item_id:
            raise ValueError("item_id not found in context.data")
            
        metadata = context.data.get("metadata", {})
        
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

    async def execute(self, context: TaskContext, results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the memory read operation.
        
        Expected context:
        - memory_store: The store instance
        - data['item_id']: str: The ID to read
        """
        store = context.memory_store
        if not store:
            raise ValueError("memory_store not found in context")
            
        item_id = context.data.get("item_id")
        if not item_id:
            raise ValueError("item_id not found in context.data")
            
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
