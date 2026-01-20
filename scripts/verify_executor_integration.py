import asyncio
import json
import respx
from httpx import Response
from backend.agents.executor.executor import ExecutorAgent
from backend.tools.registry.registry import ToolRegistry
from backend.tools.base import BaseTool, ToolDefinition
from backend.core.llm.provider import OpenAIProvider

class DummyTool(BaseTool):
    @property
    def definition(self):
        return ToolDefinition(
            name="dummy_tool",
            description="A dummy tool for smoke testing",
            parameters={
                "type": "object",
                "properties": {
                    "payload": {"type": "string"}
                },
                "required": ["payload"]
            }
        )
    async def execute(self, **kwargs):
        return {"processed": kwargs.get("payload")}

async def verify_executor():
    print("Starting Executor Integration Smoke Test...")
    
    registry = ToolRegistry()
    registry.register_tool(DummyTool())
    
    llm_provider = OpenAIProvider(model="test", base_url="http://mock-llm/v1")
    agent = ExecutorAgent(llm_client=llm_provider, registry=registry)
    
    mock_selection = {
        "tool": "dummy_tool",
        "params": {"payload": "Handshake 123"},
        "rationale": "Verifying connectivity"
    }
    
    async with respx.mock(base_url="http://mock-llm/v1") as respx_mock:
        respx_mock.post("/chat/completions").mock(return_value=Response(200, json={
            "choices": [{"message": {"content": json.dumps(mock_selection)}}]
        }))
        
        print("Executing step...")
        result = await agent.execute_step("Use the dummy tool with Handshake 123")
        
        print(f"Status: {result['status']}")
        if result['status'] == "SUCCESS":
            print(f"Tool used: {result['tool']}")
            print(f"Result: {result['result']}")
            if result['result']['processed'] == "Handshake 123":
                print("✅ SMOKE TEST PASSED")
            else:
                print("❌ SMOKE TEST FAILED: Result payload mismatch")
        else:
            print(f"❌ SMOKE TEST FAILED: {result.get('error')}")
            
    await llm_provider.close()

if __name__ == "__main__":
    asyncio.run(verify_executor())
