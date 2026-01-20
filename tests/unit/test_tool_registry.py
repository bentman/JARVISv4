import pytest
from backend.tools.registry import ToolRegistry

from backend.tools.base import BaseTool, ToolDefinition

class MockEchoTool(BaseTool):
    @property
    def definition(self):
        return ToolDefinition(
            name="echo",
            description="echoes input",
            parameters={
                "type": "object",
                "properties": {"message": {"type": "string"}},
                "required": ["message"]
            }
        )
    async def execute(self, **kwargs):
        return kwargs.get("message")

@pytest.mark.asyncio
async def test_tool_registration_and_invocation():
    registry = ToolRegistry()
    tool = MockEchoTool()
    
    registry.register_tool(tool)
    
    assert "echo" in registry.list_tools()
    
    # Test retrieval
    assert registry.get_tool("echo") == tool
    
    # Test invocation
    result = await registry.call_tool("echo", message="hello v4")
    assert result == "hello v4"

def test_list_tools_initially_empty():
    registry = ToolRegistry()
    assert registry.list_tools() == []
