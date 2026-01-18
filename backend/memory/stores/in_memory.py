"""
In-memory store implementation for JARVISv4.
"""
from typing import Dict, List, Optional
from ..schemas.memory import MemoryItem

class InMemoryStore:
    """A deterministic in-memory store for MemoryItems."""

    def __init__(self):
        self._storage: Dict[str, MemoryItem] = {}

    def put(self, item: MemoryItem):
        """Add or update an item in the store."""
        self._storage[item.id] = item

    def get(self, item_id: str) -> Optional[MemoryItem]:
        """Retrieve an item by its ID."""
        return self._storage.get(item_id)

    def list(self) -> List[MemoryItem]:
        """List all items in the store."""
        return list(self._storage.values())

    def delete(self, item_id: str):
        """Remove an item from the store."""
        if item_id in self._storage:
            del self._storage[item_id]
