"""
Deterministic orchestration engine for JARVISv4.
Established as an initial controller foundation aligned to the v3 porting plan.
"""
import logging
from typing import Dict, Any, Optional, Union
from .types import WorkflowNode, WorkflowState, TaskContext
from ..nodes.base import BaseNode

logger = logging.getLogger(__name__)

class WorkflowEngine:
    """Main workflow engine for deterministic task orchestration."""
    
    def __init__(self):
        self.nodes: Dict[str, Any] = {}
        self.state: Optional[WorkflowState] = None
        self.node_results: Dict[str, Any] = {}
        
    def add_node(self, node: Any):
        """Add a node to the workflow registry."""
        self.nodes[node.id] = node
        logger.info(f"Added node {node.id} to workflow")
        
    def get_node(self, node_id: str) -> Optional[Any]:
        """Retrieve a node by its ID."""
        return self.nodes.get(node_id)
        
    def list_nodes(self) -> list[str]:
        """List all registered node IDs."""
        return list(self.nodes.keys())

    async def execute_node(self, node_id: str, context: TaskContext) -> Dict[str, Any]:
        """
        Execute a single workflow node end-to-end.
        """
        if not isinstance(context, TaskContext):
            raise TypeError(f"Context must be TaskContext, got {type(context).__name__}")

        node = self.get_node(node_id)
        if not node:
            raise ValueError(f"Node {node_id} not found in engine")

        # In this phase, we assume nodes in the registry are executable objects
        # if they have an execute method (like BaseNode subclasses)
        if hasattr(node, "execute"):
            result = await node.execute(context, self.node_results)
            self.node_results[node_id] = result
            return result

        raise TypeError(f"Node {node_id} is not an executable node instance")

    async def execute_sequence(self, node_ids: list[str], context: TaskContext) -> Dict[str, Any]:
        """
        Execute an ordered list of nodes sequentially.
        """
        self.node_results = {}
        for node_id in node_ids:
            logger.info(f"Executing node {node_id} in sequence")
            await self.execute_node(node_id, context)
        
        return self.node_results

    async def execute_workflow(self, context: Any):
        """
        Execute the complete workflow.
        Behavior deferred to later mini-phase.
        """
        raise NotImplementedError("Multi-node workflow execution is deferred; single-node execution is available via execute_node or execute_sequence.")
