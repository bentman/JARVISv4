import asyncio
import json
import respx
import logging
from httpx import Response
from pathlib import Path
from backend.core.controller import ECFController
from backend.tools.base import BaseTool, ToolDefinition

# Setup logging to see the transition trail
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

class IntegrationTemplateTool(BaseTool):
    @property
    def definition(self):
        return ToolDefinition(
            name="integration_template_tool",
            description="A standardized tool for integration testing",
            parameters={
                "type": "object",
                "properties": {
                    "data": {"type": "string"}
                },
                "required": ["data"]
            }
        )
    async def execute(self, **kwargs):
        return {"processed_data": kwargs.get("data"), "status": "INTEGRATION_SUCCESS"}

async def first_flight():
    print("🚀 Starting First Flight: ECF Controller End-to-End Test\n")
    
    controller = ECFController()
    # Register our standard tool
    controller.registry.register_tool(IntegrationTemplateTool())
    
    goal = "Execute a first flight integration test"
    
    # Mock LLM behavior
    planner_plan = {
        "tasks": [
            {"id": "1", "description": "Run the integration template tool", "dependencies": [], "estimated_duration": "1m"}
        ]
    }
    executor_selection = {
        "tool": "integration_template_tool",
        "params": {"data": "Flight check 1-2-3"},
        "rationale": "Matches the first flight goal"
    }
    
    async with respx.mock(base_url="http://localhost:11434/v1") as respx_mock:
        # Default settings might point to localhost if not configured, or openai. 
        # OpenAIProvider in test usually gets dummy base_url or defaults.
        # Let's ensure the controller uses a predictable base_url for the mock.
        controller.llm.client.base_url = "http://mock-llm/v1"
        
        respx_mock.post("http://mock-llm/v1/chat/completions").mock(side_effect=[
            Response(200, json={"choices": [{"message": {"content": json.dumps(planner_plan)}}]}),
            Response(200, json={"choices": [{"message": {"content": json.dumps(executor_selection)}}]})
        ])
        
        print(f"Goal: {goal}")
        task_id = await controller.run_task(goal)
        
        print(f"\nFinal Task ID: {task_id}")
        print(f"Final Controller State: {controller.state.value}")
        
        # Verify result in state_manager (archive check)
        archive_path = Path("tasks/archive")
        files = list(archive_path.rglob(f"*{task_id}*"))
        if files:
            print(f"✅ SUCCESS: Task archived at {files[0]}")
        else:
            print("❌ FAILURE: Task NOT found in archive.")

if __name__ == "__main__":
    asyncio.run(first_flight())
