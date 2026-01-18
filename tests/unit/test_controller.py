import pytest
from backend.controller import WorkflowEngine, WorkflowNode, NodeType

def test_engine_initialization():
    engine = WorkflowEngine()
    assert engine.nodes == {}
    assert engine.state is None

def test_add_node():
    engine = WorkflowEngine()
    node = WorkflowNode(
        id="test-node",
        type=NodeType.LLM_WORKER,
        description="A test node"
    )
    engine.add_node(node)
    assert "test-node" in engine.list_nodes()
    assert engine.get_node("test-node").type == NodeType.LLM_WORKER

@pytest.mark.asyncio
async def test_execute_workflow_stub():
    engine = WorkflowEngine()
    with pytest.raises(NotImplementedError) as exc:
        await engine.execute_workflow(context={})
    assert "deferred" in str(exc.value)
