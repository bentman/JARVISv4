import pytest

from backend.controller.engine.engine import WorkflowEngine
from backend.controller.engine.types import TaskContext
from backend.controller.nodes.memory_op import MemoryWriteNode
from backend.memory.stores.in_memory import InMemoryStore


@pytest.mark.asyncio
async def test_memory_write_node_execution():
    """Verify that MemoryWriteNode writes to the store via the engine with deterministic ID."""
    store = InMemoryStore()
    engine = WorkflowEngine()

    node = MemoryWriteNode(
        id="mem_write_01",
        description="Test memory write",
    )
    engine.add_node(node)

    fixed_id = "test-id-123"
    context = TaskContext(
        memory_store=store,
        data={
            "content": "Test execution content",
            "item_id": fixed_id,
            "metadata": {"source": "unit_test"},
        },
    )

    result = await engine.execute_node("mem_write_01", context)

    assert result == {
        "status": "success",
        "item_id": fixed_id,
    }

    saved = store.get(fixed_id)
    assert saved is not None
    assert saved.id == fixed_id
    assert saved.content == "Test execution content"
    assert saved.metadata == {"source": "unit_test"}
