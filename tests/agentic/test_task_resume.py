import json

import pytest
import respx
from httpx import Response

from backend.core.controller import ECFController
from backend.memory.working_state import WorkingStateManager
from backend.tools.base import BaseTool, ToolDefinition


class IntegrationTemplateTool(BaseTool):
    @property
    def definition(self):
        return ToolDefinition(
            name="integration_template_tool",
            description="A standardized tool for resume testing",
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
async def test_resume_task_after_restart(tmp_path, monkeypatch):
    tasks_path = tmp_path / "tasks"
    monkeypatch.setenv("WORKING_STORAGE_PATH", str(tasks_path))

    state_manager = WorkingStateManager(tasks_path)
    task_id = state_manager.create_task({
        "goal": "Resume flow",
        "domain": "general",
        "constraints": [],
        "next_steps": [
            {"id": "1", "description": "Run the integration template tool", "dependencies": [], "estimated_duration": "1m"},
            {"id": "2", "description": "Run the integration template tool again", "dependencies": ["1"], "estimated_duration": "1m"}
        ]
    })

    controller = ECFController()
    controller.registry.register_tool(IntegrationTemplateTool())

    executor_selection_step_1 = {
        "tool": "integration_template_tool",
        "params": {"data": "Resume step 1"},
        "rationale": "Matches resume step"
    }

    async with respx.mock(base_url="http://mock-llm/v1") as respx_mock:
        controller.llm.client.base_url = "http://mock-llm/v1"
        respx_mock.post("http://mock-llm/v1/chat/completions").mock(
            return_value=Response(200, json={"choices": [{"message": {"content": json.dumps(executor_selection_step_1)}}]})
        )

        await controller.resume_task(task_id, max_steps=1)

    active_task = state_manager.load_task(task_id)
    assert active_task["status"] == "IN_PROGRESS"
    assert len(active_task["completed_steps"]) == 1
    assert active_task["current_step"] is None

    controller_restart = ECFController()
    controller_restart.registry.register_tool(IntegrationTemplateTool())

    executor_selection_step_2 = {
        "tool": "integration_template_tool",
        "params": {"data": "Resume step 2"},
        "rationale": "Matches resume step"
    }

    async with respx.mock(base_url="http://mock-llm/v1") as respx_mock:
        controller_restart.llm.client.base_url = "http://mock-llm/v1"
        respx_mock.post("http://mock-llm/v1/chat/completions").mock(
            return_value=Response(200, json={"choices": [{"message": {"content": json.dumps(executor_selection_step_2)}}]})
        )

        await controller_restart.resume_task(task_id)

    archive_files = list((tasks_path / "archive").rglob(f"*{task_id}*"))
    assert len(archive_files) == 1

    with open(archive_files[0], "r") as archived:
        archived_state = json.load(archived)

    assert archived_state["task_id"] == task_id
    assert archived_state["status"] == "COMPLETED"
    assert len(archived_state["completed_steps"]) == 2