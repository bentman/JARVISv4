from backend.memory import InMemoryStore, MemoryItem

def test_in_memory_store_operations():
    store = InMemoryStore()
    item = MemoryItem(id="test-1", content="Hello v4")
    
    # Test put
    store.put(item)
    
    # Test get
    retrieved = store.get("test-1")
    assert retrieved is not None
    assert retrieved.content == "Hello v4"
    assert retrieved.id == "test-1"
    
    # Test list
    items = store.list()
    assert len(items) == 1
    assert items[0].id == "test-1"
    
    # Test delete
    store.delete("test-1")
    assert store.get("test-1") is None
    assert len(store.list()) == 0

def test_get_nonexistent():
    store = InMemoryStore()
    assert store.get("nonexistent") is None
