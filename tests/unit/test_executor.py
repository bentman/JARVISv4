import pytest
import json
import respx
from httpx import Response
from backend.agents.executor.executor import ExecutorAgent
from backend.tools.registry.registry import ToolRegistry
from backend.tools.base import BaseTool, ToolDefinition
from backend.core.llm.provider import OpenAIProvider

class MockTool(BaseTool):
    @property
    def definition(self):
        return ToolDefinition(
            name="test_tool",
            description="A tool for testing",
            parameters={
                "type": "object",
                "properties": {
                    "input": {"type": "string"}
                },
                "required": ["input"]
            }
        )
    async def execute(self, **kwargs):
        return f"Executed with {kwargs.get('input')}"

@pytest.fixture
def registry():
    reg = ToolRegistry()
    reg.register_tool(MockTool())
    return reg

@pytest.fixture
def llm_provider():
    return OpenAIProvider(model="test", base_url="http://mock-llm/v1")

@pytest.mark.asyncio
async def test_executor_successful_tool_selection(llm_provider, registry):
    agent = ExecutorAgent(llm_client=llm_provider, registry=registry)
    
    mock_selection = {
        "tool": "test_tool",
        "params": {"input": "hello world"},
        "rationale": "Matches the request"
    }
    
    async with respx.mock(base_url="http://mock-llm/v1") as respx_mock:
        respx_mock.post("/chat/completions").mock(return_value=Response(200, json={
            "choices": [{"message": {"content": json.dumps(mock_selection)}}]
        }))
        
        result = await agent.execute_step("Run the test tool with hello world")
        
        assert result["status"] == "SUCCESS"
        assert result["result"] == "Executed with hello world"
        assert result["tool"] == "test_tool"
        
    await llm_provider.close()

@pytest.mark.asyncio
async def test_executor_no_tool_match(llm_provider, registry):
    agent = ExecutorAgent(llm_client=llm_provider, registry=registry)
    
    mock_selection = {
        "tool": "none",
        "rationale": "No tool exists for this"
    }
    
    async with respx.mock(base_url="http://mock-llm/v1") as respx_mock:
        respx_mock.post("/chat/completions").mock(return_value=Response(200, json={
            "choices": [{"message": {"content": json.dumps(mock_selection)}}]
        }))
        
        result = await agent.execute_step("Do something impossible")
        
        assert result["status"] == "FAILED"
        assert "No suitable tool found" in result["error"]
        
    await llm_provider.close()

@pytest.mark.asyncio
async def test_executor_invalid_parameters(llm_provider, registry):
    agent = ExecutorAgent(llm_client=llm_provider, registry=registry)
    
    # Missing required 'input' param
    mock_selection = {
        "tool": "test_tool",
        "params": {},
        "rationale": "Mistakenly omitted params"
    }
    
    async with respx.mock(base_url="http://mock-llm/v1") as respx_mock:
        respx_mock.post("/chat/completions").mock(return_value=Response(200, json={
            "choices": [{"message": {"content": json.dumps(mock_selection)}}]
        }))
        
        result = await agent.execute_step("Run test tool")
        
        assert result["status"] == "FAILED"
        assert "Invalid parameters" in result["error"]
        
    await llm_provider.close()
