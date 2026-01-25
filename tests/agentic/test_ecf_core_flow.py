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
async def test_ecf_first_flight_e2e(tmp_path, monkeypatch, caplog):
    # Setup isolated environment for the test
    monkeypatch.setenv("WORKING_STORAGE_PATH", str(tmp_path / "tasks"))
    monkeypatch.setenv("LLM_BASE_URL", "http://mock-llm/v1")
    monkeypatch.setenv("LLM_MODEL", "test-model")
    
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
    
    caplog.set_level("WARNING")

    async with respx.mock(base_url="http://mock-llm/v1") as respx_mock:
        respx_mock.post("http://mock-llm/v1/chat/completions").mock(side_effect=[
            Response(200, json={"choices": [{"message": {"content": json.dumps(planner_plan)}}]}),
            Response(200, json={"choices": [{"message": {"content": json.dumps(executor_selection)}}]}),
            Response(200, json={"choices": [{"message": {"content": json.dumps(executor_selection)}}]})
        ])
        
        task_id = await controller.run_task(goal)
        
        assert task_id.startswith("task_")
        assert controller.state.value == "COMPLETED"
        
        # Verify archive
        archive_files = list((tmp_path / "tasks" / "archive").rglob(f"*{task_id}*"))
        assert len(archive_files) == 1

        active_files = list((tmp_path / "tasks").glob("task_*.json"))
        assert active_files == []

        assert "Planner task_id differed from pre-created task" not in caplog.text
        
        with open(archive_files[0], "r") as f:
            saved_state = json.load(f)
            assert saved_state["status"] == "COMPLETED"
            assert saved_state["goal"] == goal
            assert "tool_name" in saved_state["completed_steps"][0]
            assert saved_state["completed_steps"][0]["tool_name"] == "integration_template_tool"


@pytest.mark.asyncio
async def test_orchestrate_task_batch_terminates_on_failure_via_analytics(tmp_path, monkeypatch):
    monkeypatch.setenv("WORKING_STORAGE_PATH", str(tmp_path / "tasks"))
    monkeypatch.setenv("LLM_BASE_URL", "http://mock-llm/v1")
    monkeypatch.setenv("LLM_MODEL", "test-model")

    controller = ECFController()
    goals = [
        "Return Task One",
        "Return Task Two",
        "Force failure"
    ]

    planner_plan = {
        "tasks": [
            {"id": "1", "description": "Return exactly: ok", "dependencies": [], "estimated_duration": "1m"}
        ]
    }
    planner_selection = {
        "tool": "text_output",
        "params": {"text": "ok"},
        "rationale": "Deterministic output"
    }
    executor_success = {
        "tool": "text_output",
        "params": {"text": "ok"},
        "rationale": "Deterministic output"
    }
    executor_failure = {
        "tool": "none",
        "rationale": "No tools"
    }

    responses = [
        planner_plan, planner_selection, executor_success,
        planner_plan, planner_selection, executor_success,
        planner_plan, planner_selection, executor_failure
    ]

    async with respx.mock(base_url="http://mock-llm/v1") as respx_mock:
        respx_mock.post("/chat/completions").mock(side_effect=[
            Response(200, json={"choices": [{"message": {"content": json.dumps(response)}}]})
            for response in responses
        ])

        result = await controller.orchestrate_task_batch(goals, max_tasks=3, min_stall_age_seconds=0)

    assert result["stop_reason"] == "failure_detected"
    assert result["task_ids"]
    assert len(result["task_ids"]) == 3

    decisions = result["decisions"]
    assert [decision["action"] for decision in decisions] == ["continue", "continue", "stop"]

    archive_dir = tmp_path / "tasks" / "archive"
    archived = list(archive_dir.rglob("*.json"))
    assert len(archived) == 3

    completed_count = 0
    failed_count = 0
    for archived_path in archived:
        with open(archived_path, "r") as archived_file:
            state = json.load(archived_file)
        if state["status"] == "COMPLETED":
            completed_count += 1
        if state["status"] == "FAILED":
            failed_count += 1
            assert state["failure_cause"] == "execution_step_failed"

    assert completed_count == 2
    assert failed_count == 1

    active_files = list((tmp_path / "tasks").glob("task_*.json"))
    assert active_files == []
