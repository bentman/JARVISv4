"""
Shared types and models for the JARVISv4 controller engine.
"""
from enum import Enum
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime, UTC

class NodeStatus(str, Enum):
    """Status of a workflow node"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"

class NodeType(str, Enum):
    """Types of workflow nodes"""
    ROUTER = "router"
    CONTEXT_BUILDER = "context_builder"
    LLM_WORKER = "llm_worker"
    TOOL_CALL = "tool_call"
    END = "end"

class WorkflowNode(BaseModel):
    """Definition of a single workflow node"""
    id: str
    type: NodeType
    description: str
    dependencies: List[str] = []
    conditions: Optional[Dict[str, Any]] = None

class WorkflowState(BaseModel):
    """Current state of a workflow execution"""
    workflow_id: str
    status: NodeStatus = NodeStatus.PENDING
    current_node: Optional[str] = None
    completed_nodes: List[str] = Field(default_factory=list)
    failed_nodes: List[str] = Field(default_factory=list)
    start_time: datetime = Field(default_factory=lambda: datetime.now(UTC))

class TaskContext(BaseModel):
    """
    Standard execution context for workflow nodes.
    Carries infrastructure (memory, tools) and shared data payload.
    """
    model_config = ConfigDict(arbitrary_types_allowed=True)

    memory_store: Any = Field(description="Memory store instance")
    tool_registry: Optional[Any] = Field(default=None, description="Tool registry instance")
    data: Dict[str, Any] = Field(default_factory=dict, description="Shared working data payload")
