import pytest
import json
import respx
from httpx import Response
from pathlib import Path
from unittest.mock import MagicMock

from backend.core.controller import ECFController, ControllerState
from backend.core.config.settings import Settings
from backend.tools.base import BaseTool, ToolDefinition

class StandardTestTool(BaseTool):
    @property
    def definition(self):
        return ToolDefinition(
            name="standard_test_tool",
            description="Testing tool",
            parameters={"type": "object", "properties": {"val": {"type": "string"}}}
        )
    async def execute(self, **kwargs):
        return f"Standard Output: {kwargs.get('val')}"

@pytest.fixture
def controller_settings(tmp_path):
    return Settings(
        app_name="TestApp",
        working_storage_path=tmp_path,
        llm_model="test-model",
        llm_base_url="http://mock-llm/v1"
    )

@pytest.mark.asyncio
async def test_controller_full_lifecycle(controller_settings):
    controller = ECFController(settings=controller_settings)
    controller.registry.register_tool(StandardTestTool())
    
    goal = "Test Full Lifecycle"
    
    # Mock LLM Responses
    # 1. Planner Response (JSON DAG)
    valid_plan = {
        "tasks": [
            {"id": "1", "description": "Run standard_test_tool", "dependencies": [], "estimated_duration": "1m"}
        ]
    }
    # 2. Executor Response (Tool Selection)
    mock_selection = {
        "tool": "standard_test_tool",
        "params": {"val": "hello-lifecycle"},
        "rationale": "Matches request"
    }
    
    async with respx.mock(base_url="http://mock-llm/v1") as respx_mock:
        # We expect two calls: one for planning, one for executing the single step
        respx_mock.post("/chat/completions").mock(side_effect=[
            Response(200, json={"choices": [{"message": {"content": json.dumps(valid_plan)}}]}),
            Response(200, json={"choices": [{"message": {"content": json.dumps(mock_selection)}}]})
        ])
        
        task_id = await controller.run_task(goal)
        
        assert task_id.startswith("task_")
        assert controller.state == ControllerState.COMPLETED
        
        # Verify file archived
        archive_dir = controller_settings.working_storage_path / "archive"
        assert archive_dir.exists()

@pytest.mark.asyncio
async def test_controller_planning_failure(controller_settings):
    controller = ECFController(settings=controller_settings)
    
    async with respx.mock(base_url="http://mock-llm/v1") as respx_mock:
        respx_mock.post("/chat/completions").mock(return_value=Response(200, json={
            "choices": [{"message": {"content": "Not JSON"}}]
        }))
        
        result = await controller.run_task("Invalid Goal")
        assert result == "FAILED_PLAN"
        assert controller.state == ControllerState.FAILED

@pytest.mark.asyncio
async def test_controller_execution_failure(controller_settings):
    controller = ECFController(settings=controller_settings)
    
    # Mock Plan
    valid_plan = {"tasks": [{"id": "1", "description": "Fail tool", "dependencies": [], "estimated_duration": "1m"}]}
    # Mock Selection (Fail)
    fail_selection = {"tool": "none", "rationale": "No tools"}
    
    async with respx.mock(base_url="http://mock-llm/v1") as respx_mock:
        respx_mock.post("/chat/completions").mock(side_effect=[
            Response(200, json={"choices": [{"message": {"content": json.dumps(valid_plan)}}]}),
            Response(200, json={"choices": [{"message": {"content": json.dumps(fail_selection)}}]})
        ])
        
        task_id = await controller.run_task("Failing Task")
        assert controller.state == ControllerState.FAILED
        
        # Verify state file reflects failure
        task_state = controller.state_manager.load_task(task_id)
        assert task_state["status"] == "FAILED"
