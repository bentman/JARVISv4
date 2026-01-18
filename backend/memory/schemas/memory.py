"""
Memory-related schemas for JARVISv4.
"""
from typing import Dict, Any, Optional
from datetime import datetime, UTC
from pydantic import BaseModel, Field

class MemoryItem(BaseModel):
    """A single record stored in memory."""
    id: str
    content: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    metadata: Dict[str, Any] = Field(default_factory=dict)
