import pytest
from backend.tools.registry import ToolRegistry

@pytest.mark.asyncio
async def test_tool_registration_and_invocation():
    registry = ToolRegistry()
    
    # Dummy tool
    async def echo(message: str) -> str:
        return message
        
    registry.register_tool("echo", echo)
    
    assert "echo" in registry.list_tools()
    
    # Test retrieval
    assert registry.get_tool("echo") == echo
    
    # Test invocation
    result = await registry.call_tool("echo", message="hello v4")
    assert result == "hello v4"

def test_list_tools_initially_empty():
    registry = ToolRegistry()
    assert registry.list_tools() == []
