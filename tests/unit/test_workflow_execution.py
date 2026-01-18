import pytest
import asyncio
from backend.controller.engine.engine import WorkflowEngine
from backend.controller.nodes.callable import CallableNode
from backend.controller.nodes.memory_op import MemoryWriteNode, MemoryReadNode
from backend.controller.engine.types import NodeType
from backend.memory.stores.in_memory import InMemoryStore

@pytest.mark.asyncio
async def test_multi_node_workflow_execution():
    """
    Test a sequential workflow:
    1. Echo input to context content
    2. Write content to memory
    3. Read back from memory
    """
    engine = WorkflowEngine()
    store = InMemoryStore()
    
    # 1. Echo node (CallableNode)
    # It takes input from context and prepares it for the next node in context
    async def echo_func(context, results):
        input_val = context.get("input")
        if not input_val:
            raise ValueError("input not found in context")
        context["content"] = f"echo: {input_val}"
        return {"output": context["content"]}
    
    echo_node = CallableNode(
        id="echo_node",
        node_type=NodeType.TOOL_CALL,
        description="Echoes input to context",
        func=echo_func
    )
    
    # 2. Memory Write Node
    write_node = MemoryWriteNode(
        id="write_node",
        description="Writes context content to memory"
    )
    
    # 3. Memory Read Node
    read_node = MemoryReadNode(
        id="read_node",
        description="Reads item back from memory"
    )
    
    engine.add_node(echo_node)
    engine.add_node(write_node)
    engine.add_node(read_node)
    
    context = {
        "memory_store": store,
        "input": "hello jarvis",
        "item_id": "test_item_1"
    }
    
    # Execute sequence
    results = await engine.execute_sequence(["echo_node", "write_node", "read_node"], context)
    
    # Assertions
    assert "echo_node" in results
    assert results["echo_node"]["output"] == "echo: hello jarvis"
    
    assert "write_node" in results
    assert results["write_node"]["status"] == "success"
    
    assert "read_node" in results
    assert results["read_node"]["status"] == "success"
    assert results["read_node"]["content"] == "echo: hello jarvis"
    
    # Verify store directly
    stored_item = store.get("test_item_1")
    assert stored_item is not None
    assert stored_item.content == "echo: hello jarvis"

@pytest.mark.asyncio
async def test_workflow_error_handling():
    """Test that missing context raises ValueError as expected."""
    engine = WorkflowEngine()
    read_node = MemoryReadNode(id="read_node", description="Read node")
    engine.add_node(read_node)
    
    # Missing memory_store in context
    context = {"item_id": "missing"}
    
    with pytest.raises(ValueError, match="memory_store not found in context"):
        await engine.execute_sequence(["read_node"], context)
