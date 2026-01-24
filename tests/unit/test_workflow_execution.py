import pytest
import asyncio
from backend.controller.engine.engine import WorkflowEngine
from backend.controller.nodes.callable import CallableNode
from backend.controller.nodes.memory_op import MemoryWriteNode, MemoryReadNode
from backend.controller.engine.types import NodeType, TaskContext
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
        # Accessing data payload per TaskContext contract
        input_val = context.data.get("input")
        if not input_val:
            raise ValueError("input not found in context.data")
        context.data["content"] = f"echo: {input_val}"
        return {"output": context.data["content"]}
    
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
    
    context = TaskContext(
        memory_store=store,
        data={
            "input": "hello jarvis",
            "item_id": "test_item_1"
        }
    )
    
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
    
    # Missing memory_store (None) in context object
    context = TaskContext(memory_store=None, data={"item_id": "missing"})
    
    with pytest.raises(ValueError, match="memory_store not found in context"):
        await engine.execute_sequence(["read_node"], context)


@pytest.mark.asyncio
async def test_workflow_missing_node_in_sequence():
    engine = WorkflowEngine()
    store = InMemoryStore()
    context = TaskContext(memory_store=store, data={"item_id": "missing"})

    with pytest.raises(ValueError, match="Node missing_node not found in engine"):
        await engine.execute_sequence(["missing_node"], context)


@pytest.mark.asyncio
async def test_workflow_invalid_context_type():
    engine = WorkflowEngine()
    with pytest.raises(TypeError, match="Context must be TaskContext"):
        await engine.execute_sequence(["any_node"], context={})  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_workflow_sequence_determinism_resets_results():
    engine = WorkflowEngine()
    store = InMemoryStore()

    async def echo_func(context, results):
        return {"output": "first"}

    echo_node = CallableNode(
        id="echo_node",
        node_type=NodeType.TOOL_CALL,
        description="Echo",
        func=echo_func
    )
    engine.add_node(echo_node)

    context = TaskContext(memory_store=store, data={})
    first_results = await engine.execute_sequence(["echo_node"], context)
    assert first_results == {"echo_node": {"output": "first"}}

    second_results = await engine.execute_sequence([], context)
    assert second_results == {}


@pytest.mark.asyncio
async def test_workflow_sequence_error_propagation_keeps_prior_results():
    engine = WorkflowEngine()
    store = InMemoryStore()

    async def ok_func(context, results):
        return {"status": "ok"}

    async def fail_func(context, results):
        raise RuntimeError("boom")

    ok_node = CallableNode(
        id="ok_node",
        node_type=NodeType.TOOL_CALL,
        description="OK",
        func=ok_func
    )
    fail_node = CallableNode(
        id="fail_node",
        node_type=NodeType.TOOL_CALL,
        description="Fail",
        func=fail_func
    )
    engine.add_node(ok_node)
    engine.add_node(fail_node)

    context = TaskContext(memory_store=store, data={})

    with pytest.raises(RuntimeError, match="boom"):
        await engine.execute_sequence(["ok_node", "fail_node"], context)

    assert engine.node_results == {"ok_node": {"status": "ok"}}
