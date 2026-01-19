"""
Integration test for Workflow Engine persistence using SQLite memory.
"""
import pytest
from pathlib import Path
from backend.core.config.settings import Settings
from backend.memory.factory import create_memory_store
from backend.controller.engine.engine import WorkflowEngine
from backend.controller.engine.types import TaskContext
from backend.controller.nodes.memory_op import MemoryWriteNode
from backend.memory.stores.sqlite_store import SQLiteStore
from backend.memory.schemas.memory import MemoryItem

@pytest.mark.asyncio
async def test_workflow_engine_persistence(tmp_path):
    """
    Test that a workflow executing a memory write node persists data to SQLite,
    verified by reading from a fresh store instance.
    """
    # 1. Setup - Configure for SQLite with a temp path
    db_path = tmp_path / "workflow_test.db"
    settings = Settings(
        memory_store_type="sqlite",
        memory_db_path=db_path
    )
    
    # 2. Create Store A via factory
    store_a = create_memory_store(settings)
    
    # 3. Setup Workflow Engine and Context
    engine = WorkflowEngine()
    write_node = MemoryWriteNode(
        id="write_step",
        description="Write persistence test data"
    )
    engine.add_node(write_node)
    
    context = TaskContext(
        memory_store=store_a,
        data={
            "item_id": "wf-persist-1",
            "content": "Persisted via WorkflowEngine",
            "metadata": {"source": "integration_test"}
        }
    )
    
    # 4. Execute Write via Engine
    await engine.execute_node("write_step", context)
    
    # 5. Verify Persistence - Create Store B (fresh instance)
    # Using factory again to prove config consistency, though direct init works too
    store_b = create_memory_store(settings)
    
    # 6. Assertions
    retrieved = store_b.get("wf-persist-1")
    assert retrieved is not None
    assert retrieved.content == "Persisted via WorkflowEngine"
    assert retrieved.metadata["source"] == "integration_test"
