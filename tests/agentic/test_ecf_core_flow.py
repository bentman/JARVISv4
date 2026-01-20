import asyncio
import json
import pytest
import respx
from httpx import Response
from pathlib import Path
from backend.core.controller import ECFController
from backend.tools.base import BaseTool, ToolDefinition

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

@pytest.mark.asyncio
async def test_ecf_first_flight_e2e(tmp_path, monkeypatch):
    # Setup isolated environment for the test
    monkeypatch.setenv("WORKING_STORAGE_PATH", str(tmp_path / "tasks"))
    
    controller = ECFController()
    controller.registry.register_tool(IntegrationTemplateTool())
    
    goal = "Execute a first flight integration test"
    
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
    
    async with respx.mock(base_url="http://mock-llm/v1") as respx_mock:
        controller.llm.client.base_url = "http://mock-llm/v1"
        
        respx_mock.post("http://mock-llm/v1/chat/completions").mock(side_effect=[
            Response(200, json={"choices": [{"message": {"content": json.dumps(planner_plan)}}]}),
            Response(200, json={"choices": [{"message": {"content": json.dumps(executor_selection)}}]})
        ])
        
        task_id = await controller.run_task(goal)
        
        assert task_id.startswith("task_")
        assert controller.state.value == "COMPLETED"
        
        # Verify archive
        archive_files = list((tmp_path / "tasks" / "archive").rglob(f"*{task_id}*"))
        assert len(archive_files) == 1
        
        with open(archive_files[0], "r") as f:
            saved_state = json.load(f)
            assert saved_state["status"] == "COMPLETED"
            assert saved_state["goal"] == goal
            assert "tool_name" in saved_state["completed_steps"][0]
            assert saved_state["completed_steps"][0]["tool_name"] == "integration_template_tool"
