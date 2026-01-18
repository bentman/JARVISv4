"""
Unit tests for memory operation nodes.
"""
import pytest
from backend.controller.engine.engine import WorkflowEngine
from backend.controller.nodes.memory_op import MemoryWriteNode
from backend.memory.stores.in_memory import InMemoryStore

@pytest.mark.asyncio
async def test_memory_write_node_execution():
    """Verify that MemoryWriteNode writes to the store via the engine with deterministic ID."""
    # Setup
    store = InMemoryStore()
    engine = WorkflowEngine()
    
    node = MemoryWriteNode(
        id="mem_write_01",
        description="Test memory write"
    )
    engine.add_node(node)
    
    fixed_id = "test-id-123"
    context = {
        "memory_store": store,
        "content": "Test execution content",
        "item_id": fixed_id,
        "metadata": {"source": "unit_test"}
    }
    
    # Execute
    result = await engine.execute_node("mem_write_01", context)
    
    # Verify execution result (deterministic)
    assert result == {
        "status": "success",
        "item_id": fixed_id
    }
    
    # Verify store state
    stored_item = store.get(fixed_id)
    assert stored_item is not None
    assert stored_item.content == "Test execution content"
    assert stored_item.metadata["source"] == "unit_test"
    assert stored_item.id == fixed_id
