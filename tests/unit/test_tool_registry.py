import pytest
from backend.tools.registry import ToolRegistry
from backend.tools.registry.registry import (
    ToolNotFoundError,
    ToolParameterValidationError,
    ToolExecutionError,
)

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


@pytest.mark.asyncio
async def test_tool_registry_missing_tool_error():
    registry = ToolRegistry()
    with pytest.raises(ToolNotFoundError, match="Tool 'missing' not found"):
        await registry.call_tool("missing")


@pytest.mark.asyncio
async def test_tool_registry_invalid_params_error():
    registry = ToolRegistry()
    registry.register_tool(MockEchoTool())

    with pytest.raises(ToolParameterValidationError, match="Invalid parameters for tool 'echo'"):
        await registry.call_tool("echo")


@pytest.mark.asyncio
async def test_tool_registry_execution_error():
    class FailingTool(MockEchoTool):
        async def execute(self, **kwargs):
            raise RuntimeError("boom")

    registry = ToolRegistry()
    registry.register_tool(FailingTool())

    with pytest.raises(ToolExecutionError, match="Tool 'echo' execution failed: boom"):
        await registry.call_tool("echo", message="hi")
