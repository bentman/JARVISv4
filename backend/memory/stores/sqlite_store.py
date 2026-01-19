"""
SQLite-backed store implementation for JARVISv4.
"""
import sqlite3
import json
from typing import List, Optional
from datetime import datetime, UTC
from pathlib import Path
from ..schemas.memory import MemoryItem

class SQLiteStore:
    """
    A persistent SQLite-backed store for MemoryItems.
    
    Persists MemoryItem fields:
    - id (TEXT PRIMARY KEY)
    - content (TEXT)
    - timestamp (TEXT ISO8601)
    - metadata (TEXT JSON)
    """

    def __init__(self, db_path: str):
        """
        Initialize the SQLite store.
        
        Args:
            db_path: Path to the SQLite database file.
        """
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize the database schema if it doesn't exist."""
        # Ensure directory exists
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memory_items (
                    id TEXT PRIMARY KEY,
                    content TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    metadata TEXT NOT NULL
                )
            """)
            conn.commit()

    def put(self, item: MemoryItem):
        """Add or update an item in the store."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO memory_items (id, content, timestamp, metadata)
                VALUES (?, ?, ?, ?)
                """,
                (
                    item.id,
                    item.content,
                    item.timestamp.isoformat(),
                    json.dumps(item.metadata)
                )
            )
            conn.commit()

    def get(self, item_id: str) -> Optional[MemoryItem]:
        """Retrieve an item by its ID."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT id, content, timestamp, metadata FROM memory_items WHERE id = ?",
                (item_id,)
            )
            row = cursor.fetchone()
            
            if not row:
                return None
                
            return MemoryItem(
                id=row[0],
                content=row[1],
                timestamp=datetime.fromisoformat(row[2]),
                metadata=json.loads(row[3])
            )

    def list(self) -> List[MemoryItem]:
        """List all items in the store."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT id, content, timestamp, metadata FROM memory_items")
            rows = cursor.fetchall()
            
            return [
                MemoryItem(
                    id=row[0],
                    content=row[1],
                    timestamp=datetime.fromisoformat(row[2]),
                    metadata=json.loads(row[3])
                )
                for row in rows
            ]

    def delete(self, item_id: str):
        """Remove an item from the store."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM memory_items WHERE id = ?", (item_id,))
            conn.commit()
