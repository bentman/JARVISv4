import pytest
from backend.controller import WorkflowEngine, NodeType
from backend.controller.nodes.callable import CallableNode
from backend.memory import InMemoryStore, MemoryItem
from backend.tools.registry import ToolRegistry

@pytest.mark.asyncio
async def test_node_execution_with_memory_and_tools():
    # 1. Setup registries and store
    tool_registry = ToolRegistry()
    memory_store = InMemoryStore()
    engine = WorkflowEngine()
    
    # 2. Register a tool
    async def mock_tool(input_val: str) -> str:
        return f"processed: {input_val}"
    
    tool_registry.register_tool("mock_tool", mock_tool)
    
    # 3. Create a node that uses tools and memory
    async def node_logic(ctx, results):
        # Call tool
        tool_res = await ctx["tools"].call_tool("mock_tool", input_val="data")
        
        # Write to memory
        item = MemoryItem(id="node-res", content=tool_res)
        ctx["memory"].put(item)
        
        return {"output": tool_res}
        
    node = CallableNode(
        id="test-node",
        node_type=NodeType.TOOL_CALL,
        description="A node that exercises tools and memory",
        func=node_logic
    )
    engine.add_node(node)
    
    # 4. Execute
    context = {
        "tools": tool_registry,
        "memory": memory_store
    }
    
    result = await engine.execute_node("test-node", context)
    
    # 5. Assertions
    assert result["output"] == "processed: data"
    assert engine.node_results["test-node"] == result
    
    # Verify memory
    stored = memory_store.get("node-res")
    assert stored is not None
    assert stored.content == "processed: data"
