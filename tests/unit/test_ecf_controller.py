import pytest
import json
import respx
import sqlite3
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
        respx_mock.post("/chat/completions").mock(side_effect=[
            Response(200, json={"choices": [{"message": {"content": json.dumps(valid_plan)}}]}),
            Response(200, json={"choices": [{"message": {"content": json.dumps(mock_selection)}}]}),
            Response(200, json={"choices": [{"message": {"content": json.dumps(mock_selection)}}]})
        ])
        
        task_id = await controller.run_task(goal)
        
        assert task_id.startswith("task_")
        assert controller.state == ControllerState.COMPLETED
        
        # Verify file archived
        archive_dir = controller_settings.working_storage_path / "archive"
        assert archive_dir.exists()

        trace_db_path = controller_settings.working_storage_path / "traces.db"
        with sqlite3.connect(trace_db_path) as conn:
            decision_count = conn.execute("SELECT COUNT(*) FROM trace_decisions").fetchone()[0]
            tool_call_count = conn.execute("SELECT COUNT(*) FROM trace_tool_calls").fetchone()[0]
            validation_count = conn.execute("SELECT COUNT(*) FROM trace_validations").fetchone()[0]

        assert decision_count >= 1
        assert tool_call_count >= 1
        assert validation_count >= 1

@pytest.mark.asyncio
async def test_controller_planning_failure(controller_settings):
    controller = ECFController(settings=controller_settings)
    
    async with respx.mock(base_url="http://mock-llm/v1") as respx_mock:
        respx_mock.post("/chat/completions").mock(return_value=Response(200, json={
            "choices": [{"message": {"content": "Not JSON"}}]
        }))
        
        result = await controller.run_task("Invalid Goal")
        assert result.startswith("task_")
        assert controller.state == ControllerState.FAILED
        
        archive_dir = controller_settings.working_storage_path / "archive"
        archived = list(archive_dir.rglob("*failed_plan.json"))
        assert len(archived) == 1
        with open(archived[0], "r") as f:
            archived_state = json.load(f)
            assert archived_state["status"] == "FAILED"
            assert archived_state["failure_cause"] == "planning_invalid"

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
        
        archive_dir = controller_settings.working_storage_path / "archive"
        archived = list(archive_dir.rglob("*failed_plan.json"))
        assert len(archived) == 1
        with open(archived[0], "r") as f:
            archived_state = json.load(f)
            assert archived_state["status"] == "FAILED"
            assert "error" in archived_state
            assert "not executable" in archived_state["error"]


@pytest.mark.asyncio
async def test_controller_tool_exception_archives(controller_settings):
    controller = ECFController(settings=controller_settings)

    valid_plan = {
        "tasks": [
            {"id": "1", "description": "Run standard_test_tool", "dependencies": [], "estimated_duration": "1m"}
        ]
    }
    
    async def raise_execute_step(*_, **__):
        raise RuntimeError("tool failure")

    guardrail_selection = {
        "tool": "text_output",
        "params": {"text": "ok"},
        "rationale": "Registered tool for planning"
    }

    async with respx.mock(base_url="http://mock-llm/v1") as respx_mock:
        respx_mock.post("/chat/completions").mock(side_effect=[
            Response(200, json={"choices": [{"message": {"content": json.dumps(valid_plan)}}]}),
            Response(200, json={"choices": [{"message": {"content": json.dumps(guardrail_selection)}}]})
        ])
        
        with pytest.MonkeyPatch.context() as monkeypatch:
            monkeypatch.setattr(controller.executor, "execute_step", raise_execute_step)
            task_id = await controller.run_task("Tool Exception")

        assert controller.state == ControllerState.FAILED

        archive_dir = controller_settings.working_storage_path / "archive"
        archived = list(archive_dir.rglob("*error.json"))
        assert len(archived) == 1
        with open(archived[0], "r") as f:
            archived_state = json.load(f)
            assert archived_state["status"] == "FAILED"
        assert task_id.startswith("task_")


@pytest.mark.asyncio
async def test_controller_rejects_plan_with_unknown_tool_fails_in_planning(controller_settings):
    controller = ECFController(settings=controller_settings)
    controller.registry.register_tool(StandardTestTool())

    invalid_plan = {
        "tasks": [
            {"id": "1", "description": "Do an impossible step", "dependencies": [], "estimated_duration": "1m"}
        ]
    }

    async def fail_if_called(*_, **__):
        raise AssertionError("executor should not run")

    async with respx.mock(base_url="http://mock-llm/v1") as respx_mock:
        respx_mock.post("/chat/completions").mock(return_value=Response(200, json={
            "choices": [{"message": {"content": json.dumps(invalid_plan)}}]
        }))

        with pytest.MonkeyPatch.context() as monkeypatch:
            monkeypatch.setattr(controller.executor, "execute_step", fail_if_called)
            task_id = await controller.run_task("Unknown Tool Planning")

    assert controller.state == ControllerState.FAILED

    archive_dir = controller_settings.working_storage_path / "archive"
    archived = list(archive_dir.rglob("*failed_plan.json"))
    assert len(archived) == 1
    with open(archived[0], "r") as f:
        archived_state = json.load(f)
        assert archived_state["status"] == "FAILED"
        assert "error" in archived_state
        assert "not executable" in archived_state["error"]
    assert task_id.startswith("task_")


@pytest.mark.asyncio
async def test_controller_rejects_plan_exceeding_max_planned_steps(controller_settings):
    controller = ECFController(settings=controller_settings)
    controller.registry.register_tool(StandardTestTool())

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(controller, "MAX_PLANNED_STEPS", 1)

        invalid_plan = {
            "tasks": [
                {"id": "1", "description": "Run standard_test_tool", "dependencies": [], "estimated_duration": "1m"},
                {"id": "2", "description": "Run standard_test_tool", "dependencies": ["1"], "estimated_duration": "1m"}
            ]
        }

        async with respx.mock(base_url="http://mock-llm/v1") as respx_mock:
            respx_mock.post("/chat/completions").mock(return_value=Response(200, json={
                "choices": [{"message": {"content": json.dumps(invalid_plan)}}]
            }))

            task_id = await controller.run_task("Plan too long")

    assert controller.state == ControllerState.FAILED

    archive_dir = controller_settings.working_storage_path / "archive"
    archived = list(archive_dir.rglob("*failed_plan.json"))
    assert len(archived) == 1
    with open(archived[0], "r") as f:
        archived_state = json.load(f)
        assert archived_state["status"] == "FAILED"
        assert archived_state["failure_cause"] == "planning_invalid"
        assert "MAX_PLANNED_STEPS" in archived_state["error"]
    assert task_id.startswith("task_")


@pytest.mark.asyncio
async def test_controller_fails_when_max_executed_steps_exceeded(controller_settings):
    controller = ECFController(settings=controller_settings)
    controller.registry.register_tool(StandardTestTool())

    valid_plan = {
        "tasks": [
            {"id": "1", "description": "Run standard_test_tool", "dependencies": [], "estimated_duration": "1m"},
            {"id": "2", "description": "Run standard_test_tool", "dependencies": ["1"], "estimated_duration": "1m"}
        ]
    }
    guardrail_selection = {
        "tool": "standard_test_tool",
        "params": {"val": "hello-cap"},
        "rationale": "Matches request"
    }

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(controller, "MAX_EXECUTED_STEPS", 1)

        async with respx.mock(base_url="http://mock-llm/v1") as respx_mock:
            respx_mock.post("/chat/completions").mock(side_effect=[
                Response(200, json={"choices": [{"message": {"content": json.dumps(valid_plan)}}]}),
                Response(200, json={"choices": [{"message": {"content": json.dumps(guardrail_selection)}}]}),
                Response(200, json={"choices": [{"message": {"content": json.dumps(guardrail_selection)}}]}),
                Response(200, json={"choices": [{"message": {"content": json.dumps(guardrail_selection)}}]})
            ])

            task_id = await controller.run_task("Execution cap")

    assert controller.state == ControllerState.FAILED

    archive_dir = controller_settings.working_storage_path / "archive"
    archived = list(archive_dir.rglob("*failed_execute.json"))
    assert len(archived) == 1
    with open(archived[0], "r") as f:
        archived_state = json.load(f)
        assert archived_state["status"] == "FAILED"
        assert archived_state["failure_cause"] == "execution_step_failed"
        assert "MAX_EXECUTED_STEPS" in archived_state["error"]
    assert task_id.startswith("task_")
