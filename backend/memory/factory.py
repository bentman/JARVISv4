"""
Factory for creating memory store instances based on settings.
"""
from typing import Any
from ..core.config.settings import Settings
from .stores.in_memory import InMemoryStore
from .stores.sqlite_store import SQLiteStore

def create_memory_store(settings: Settings) -> Any:
    """
    Create and return the configured memory store instance.
    
    Args:
        settings: Application settings containing memory configuration.
        
    Returns:
        An instance of InMemoryStore or SQLiteStore.
    """
    store_type = settings.memory_store_type.lower()
    
    if store_type == "sqlite":
        # SQLiteStore handles parent directory creation internally
        return SQLiteStore(str(settings.memory_db_path))
    
    return InMemoryStore()
