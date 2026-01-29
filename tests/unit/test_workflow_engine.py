"""
Unit tests for the enhanced WorkflowEngine with v3 execution logic.
Tests focus on linear workflow execution while preserving existing interfaces.
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock
from backend.controller.engine.engine import WorkflowEngine
from backend.controller.engine.types import WorkflowNode, WorkflowState, TaskContext, NodeStatus, NodeType
from backend.controller.nodes.base import BaseNode


class MockNode(BaseNode):
    """Mock node for testing workflow engine."""
    
    def __init__(self, node_id: str, node_type: NodeType, description: str, should_fail: bool = False):
        super().__init__(node_id, node_type, description)
        self.should_fail = should_fail
        self.execute_called = False
        self.dependencies = []
    
    async def execute(self, context: TaskContext, results: dict) -> dict:
        """Mock execution that can optionally fail."""
        self.execute_called = True
        if self.should_fail:
            raise Exception("Mock node execution failed")
        return {"node_id": self.id, "result": "success", "context_data": context.data}


class TestWorkflowEngine:
    """Test cases for the enhanced WorkflowEngine."""
    
    def test_add_node_preserves_interface(self):
        """Test that add_node works as expected."""
        engine = WorkflowEngine()
        node = MockNode("test_node", NodeType.ROUTER, "Test node")
        engine.add_node(node)
        assert engine.get_node("test_node") == node
        assert "test_node" in engine.list_nodes()
    
    def test_get_node_returns_registered_node(self):
        """Test that get_node returns the correct node."""
        engine = WorkflowEngine()
        node = MockNode("test_node", NodeType.ROUTER, "Test node")
        engine.add_node(node)
        retrieved = engine.get_node("test_node")
        assert retrieved == node
        assert engine.get_node("nonexistent") is None
    
    def test_list_nodes_returns_all_ids(self):
        """Test that list_nodes returns all registered node IDs."""
        engine = WorkflowEngine()
        node1 = MockNode("node1", NodeType.ROUTER, "Node 1")
        node2 = MockNode("node2", NodeType.CONTEXT_BUILDER, "Node 2")
        engine.add_node(node1)
        engine.add_node(node2)
        node_ids = engine.list_nodes()
        assert set(node_ids) == {"node1", "node2"}
    
    @pytest.mark.asyncio
    async def test_execute_node_with_valid_context(self):
        """Test that execute_node works with valid context."""
        engine = WorkflowEngine()
        node = MockNode("test_node", NodeType.ROUTER, "Test node")
        engine.add_node(node)
        
        context = TaskContext(
            memory_store=Mock(),
            tool_registry=Mock(),
            data={"test": "data"}
        )
        
        result = await engine.execute_node("test_node", context)
        assert result == {"node_id": "test_node", "result": "success", "context_data": {"test": "data"}}
        assert node.execute_called
    
    @pytest.mark.asyncio
    async def test_execute_node_with_invalid_context(self):
        """Test that execute_node raises TypeError with invalid context."""
        engine = WorkflowEngine()
        node = MockNode("test_node", NodeType.ROUTER, "Test node")
        engine.add_node(node)
        
        with pytest.raises(TypeError, match="Context must be TaskContext"):
            await engine.execute_node("test_node", "invalid_context")
    
    @pytest.mark.asyncio
    async def test_execute_node_with_nonexistent_node(self):
        """Test that execute_node raises ValueError for nonexistent node."""
        engine = WorkflowEngine()
        context = TaskContext(
            memory_store=Mock(),
            tool_registry=Mock(),
            data={}
        )
        
        with pytest.raises(ValueError, match="Node nonexistent not found in engine"):
            await engine.execute_node("nonexistent", context)
    
    @pytest.mark.asyncio
    async def test_execute_sequence_linear_execution(self):
        """Test that execute_sequence executes nodes in order."""
        engine = WorkflowEngine()
        node1 = MockNode("node1", NodeType.ROUTER, "Node 1")
        node2 = MockNode("node2", NodeType.CONTEXT_BUILDER, "Node 2")
        engine.add_node(node1)
        engine.add_node(node2)
        
        context = TaskContext(
            memory_store=Mock(),
            tool_registry=Mock(),
            data={}
        )
        
        result = await engine.execute_sequence(["node1", "node2"], context)
        assert result == {
            "node1": {"node_id": "node1", "result": "success", "context_data": {}},
            "node2": {"node_id": "node2", "result": "success", "context_data": {}}
        }
        assert node1.execute_called
        assert node2.execute_called
    
    @pytest.mark.asyncio
    async def test_execute_workflow_linear_path(self):
        """Test that execute_workflow executes linear workflow successfully."""
        engine = WorkflowEngine()
        node1 = MockNode("node1", NodeType.ROUTER, "Node 1")
        node2 = MockNode("node2", NodeType.CONTEXT_BUILDER, "Node 2")
        node2.dependencies = ["node1"]  # node2 depends on node1
        engine.add_node(node1)
        engine.add_node(node2)
        
        context = TaskContext(
            memory_store=Mock(),
            tool_registry=Mock(),
            data={"workflow_id": "test_workflow"}
        )
        
        result = await engine.execute_workflow(context)
        assert result["status"] == "completed"
        assert result["workflow_id"] == "test_workflow"
        assert "node1" in result["results"]
        assert "node2" in result["results"]
        assert node1.execute_called
        assert node2.execute_called
        assert engine.state is not None
        assert engine.state.status == NodeStatus.COMPLETED
    
    @pytest.mark.asyncio
    async def test_execute_workflow_with_dependencies(self):
        """Test that execute_workflow handles dependency ordering correctly."""
        engine = WorkflowEngine()
        node1 = MockNode("node1", NodeType.ROUTER, "Node 1")
        node2 = MockNode("node2", NodeType.CONTEXT_BUILDER, "Node 2")
        node3 = MockNode("node3", NodeType.LLM_WORKER, "Node 3")
        node2.dependencies = ["node1"]
        node3.dependencies = ["node2"]
        engine.add_node(node1)
        engine.add_node(node2)
        engine.add_node(node3)
        
        context = TaskContext(
            memory_store=Mock(),
            tool_registry=Mock(),
            data={"workflow_id": "test_workflow"}
        )
        
        result = await engine.execute_workflow(context)
        assert result["status"] == "completed"
        assert "node1" in result["results"]
        assert "node2" in result["results"]
        assert "node3" in result["results"]
        assert node1.execute_called
        assert node2.execute_called
        assert node3.execute_called
    
    @pytest.mark.asyncio
    async def test_execute_workflow_node_failure_handling(self):
        """Test that execute_workflow handles node failures correctly."""
        engine = WorkflowEngine()
        node1 = MockNode("node1", NodeType.ROUTER, "Node 1")
        node2 = MockNode("node2", NodeType.CONTEXT_BUILDER, "Node 2", should_fail=True)
        node2.dependencies = ["node1"]
        engine.add_node(node1)
        engine.add_node(node2)
        
        context = TaskContext(
            memory_store=Mock(),
            tool_registry=Mock(),
            data={"workflow_id": "test_workflow"}
        )
        
        result = await engine.execute_workflow(context)
        assert result["status"] == "failed"
        assert "Mock node execution failed" in result["error"]
        assert engine.state is not None
        assert engine.state.status == NodeStatus.FAILED
        assert "node1" in engine.state.completed_nodes
        assert "node2" in engine.state.failed_nodes
    
    @pytest.mark.asyncio
    async def test_execute_workflow_state_tracking(self):
        """Test that execute_workflow properly tracks state during execution."""
        engine = WorkflowEngine()
        node1 = MockNode("node1", NodeType.ROUTER, "Node 1")
        node2 = MockNode("node2", NodeType.CONTEXT_BUILDER, "Node 2")
        node2.dependencies = ["node1"]
        engine.add_node(node1)
        engine.add_node(node2)
        
        context = TaskContext(
            memory_store=Mock(),
            tool_registry=Mock(),
            data={"workflow_id": "test_workflow"}
        )
        
        result = await engine.execute_workflow(context)
        assert engine.state is not None
        assert engine.state.workflow_id == "test_workflow"
        assert engine.state.status == NodeStatus.COMPLETED
        assert "node1" in engine.state.completed_nodes
        assert "node2" in engine.state.completed_nodes
        assert engine.state.current_node is None  # Should be reset after completion
    
    @pytest.mark.asyncio
    async def test_execute_workflow_no_starting_nodes(self):
        """Test that execute_workflow raises error when no starting nodes exist."""
        engine = WorkflowEngine()
        node1 = MockNode("node1", NodeType.ROUTER, "Node 1")
        node1.dependencies = ["nonexistent"]  # Depends on non-existent node
        engine.add_node(node1)
        
        context = TaskContext(
            memory_store=Mock(),
            tool_registry=Mock(),
            data={}
        )
        
        result = await engine.execute_workflow(context)
        assert result["status"] == "failed"
        assert "No starting nodes found in workflow" in result["error"]
