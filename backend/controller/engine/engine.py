"""
Deterministic orchestration engine for JARVISv4.
Ported core execution logic from JARVISv3 workflow engine for linear workflow execution.
"""
import logging
import asyncio
from typing import Dict, Any, Optional, List
from .types import WorkflowNode, WorkflowState, TaskContext, NodeStatus, NodeType
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
        Preserves existing interface for backward compatibility.
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
        Preserves existing interface for backward compatibility.
        """
        self.node_results = {}
        for node_id in node_ids:
            logger.info(f"Executing node {node_id} in sequence")
            await self.execute_node(node_id, context)
        
        return self.node_results

    async def execute_workflow(self, context: TaskContext) -> Dict[str, Any]:
        """
        Execute the complete workflow using v3 state machine logic for linear execution.
        This replaces the NotImplementedError with functional workflow execution.
        """
        if not isinstance(context, TaskContext):
            raise TypeError(f"Context must be TaskContext, got {type(context).__name__}")

        # Initialize workflow state
        start_time = context.data.get("start_time")
        if start_time is None:
            from datetime import datetime, UTC
            start_time = datetime.now(UTC)
        
        self.state = WorkflowState(
            workflow_id=context.data.get("workflow_id", "default_workflow"),
            start_time=start_time
        )
        
        try:
            # Find starting nodes (nodes with no dependencies)
            start_nodes = [node_id for node_id, node in self.nodes.items() 
                          if not node.dependencies]
            
            if not start_nodes:
                raise ValueError("No starting nodes found in workflow")
            
            # For linear execution, use the first start node and follow dependencies
            if len(start_nodes) == 1:
                await self._execute_linear_workflow(start_nodes[0])
            else:
                # Multiple start nodes - execute in dependency order
                await self._execute_linear_workflow_with_dependencies(start_nodes)
            
            # Complete workflow
            final_result = {
                "status": "completed",
                "workflow_id": self.state.workflow_id,
                "execution_time": 0.0,
                "results": self.node_results
            }
            if self.state:
                self.state.status = NodeStatus.COMPLETED
                workflow_start = context.data.get("start_time") or self.state.start_time
                final_result["execution_time"] = (self.state.start_time - workflow_start).total_seconds()
            
            logger.info("Workflow completed successfully")
            return final_result
            
        except Exception as e:
            error_msg = str(e) or type(e).__name__
            logger.error(f"Workflow failed: {error_msg}")
            if self.state:
                self.state.status = NodeStatus.FAILED
            
            return {
                "status": "failed",
                "error": error_msg,
                "workflow_id": self.state.workflow_id if self.state else None,
                "execution_time": 0.0
            }

    async def _execute_linear_workflow(self, start_node_id: str):
        """Execute workflow linearly from start node following dependencies."""
        current_node_id = start_node_id
        executed_nodes = set()
        
        while current_node_id and current_node_id not in executed_nodes:
            await self._execute_single_node(current_node_id)
            executed_nodes.add(current_node_id)
            
            # Find next node in dependency chain
            next_nodes = [nid for nid, node in self.nodes.items() 
                         if current_node_id in node.dependencies]
            
            if next_nodes:
                # For linear execution, take the first next node
                current_node_id = next_nodes[0]
            else:
                current_node_id = None

    async def _execute_linear_workflow_with_dependencies(self, start_nodes: List[str]):
        """Execute workflow handling multiple start nodes with dependency ordering."""
        # Simple topological sort for linear execution
        executed = set()
        pending = set(start_nodes)
        
        while pending:
            # Execute all nodes that have their dependencies satisfied
            ready_nodes = []
            for node_id in list(pending):
                node = self.nodes[node_id]
                if all(dep in executed for dep in node.dependencies):
                    ready_nodes.append(node_id)
                    pending.remove(node_id)
            
            # Execute ready nodes in order
            for node_id in ready_nodes:
                await self._execute_single_node(node_id)
                executed.add(node_id)
                # Add dependent nodes to pending
                dependent_nodes = [nid for nid, node in self.nodes.items() 
                                 if node_id in node.dependencies and nid not in executed]
                pending.update(dependent_nodes)

    async def _execute_single_node(self, node_id: str):
        """Execute a single node with state tracking."""
        if self.state:
            self.state.current_node = node_id
            self.state.status = NodeStatus.RUNNING
        
        try:
            # Execute the node
            node = self.get_node(node_id)
            if not node:
                raise ValueError(f"Node {node_id} not found in engine")
            
            if hasattr(node, "execute"):
                result = await node.execute(self._create_node_context(node_id), self.node_results)
                self.node_results[node_id] = result
            else:
                raise TypeError(f"Node {node_id} is not an executable node instance")
            
            # Update state on success
            if self.state:
                self.state.completed_nodes.append(node_id)
                self.state.status = NodeStatus.COMPLETED
                
        except Exception as e:
            # Update state on failure
            if self.state:
                self.state.failed_nodes.append(node_id)
                self.state.status = NodeStatus.FAILED
            raise e
        finally:
            if self.state:
                self.state.current_node = None

    def _create_node_context(self, node_id: str) -> TaskContext:
        """Create a context for the current node execution."""
        # For now, return a minimal context - this could be enhanced later
        # to include node-specific information
        return TaskContext(
            memory_store=None,  # Will be set by caller
            tool_registry=None,  # Will be set by caller
            data={"node_id": node_id, "node_type": self.nodes[node_id].type}
        )