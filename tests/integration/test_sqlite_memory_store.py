"""
Integration tests for SQLite Memory Store persistence.
"""
import pytest
import os
from datetime import datetime, UTC
from backend.memory.stores.sqlite_store import SQLiteStore
from backend.memory.schemas.memory import MemoryItem

@pytest.fixture
def test_db_path(tmp_path):
    """Provide a temporary database path."""
    return str(tmp_path / "test_memory.db")

def test_sqlite_store_persistence(test_db_path):
    """
    Test that data persists across store instances (simulating restart).
    """
    # 1. Create first instance and write data
    store1 = SQLiteStore(test_db_path)
    original_item = MemoryItem(
        id="test-1",
        content="Persistent content",
        timestamp=datetime.now(UTC),
        metadata={"source": "integration_test", "priority": 1}
    )
    store1.put(original_item)
    
    # Verify it exists in store1
    assert store1.get("test-1") is not None
    
    # 2. "Restart" - create a NEW instance pointing to the same DB file
    store2 = SQLiteStore(test_db_path)
    
    # 3. Read back from new instance
    retrieved_item = store2.get("test-1")
    
    # 4. Validate all fields match
    assert retrieved_item is not None
    assert retrieved_item.id == original_item.id
    assert retrieved_item.content == original_item.content
    assert retrieved_item.timestamp == original_item.timestamp
    assert retrieved_item.metadata == original_item.metadata
    
    # 5. Validate listing work
    items = store2.list()
    assert len(items) == 1
    assert items[0].id == "test-1"

def test_sqlite_store_delete(test_db_path):
    """Test deletion persists."""
    store = SQLiteStore(test_db_path)
    item = MemoryItem(id="del-1", content="To be deleted")
    store.put(item)
    
    assert store.get("del-1") is not None
    store.delete("del-1")
    assert store.get("del-1") is None
    
    # Verify persistence of deletion
    store_new = SQLiteStore(test_db_path)
    assert store_new.get("del-1") is None
