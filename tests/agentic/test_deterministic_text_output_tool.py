import json
import pytest
import respx
from httpx import Response

from backend.core.controller import ECFController


@pytest.mark.asyncio
async def test_deterministic_text_output_tool_e2e(tmp_path, monkeypatch):
    monkeypatch.setenv("WORKING_STORAGE_PATH", str(tmp_path / "tasks"))
    monkeypatch.setenv("LLM_BASE_URL", "http://mock-llm/v1")
    monkeypatch.setenv("LLM_MODEL", "test-model")

    controller = ECFController()
    goal = "Return a deterministic string using the text_output tool"

    planner_plan = {
        "tasks": [
            {
                "id": "1",
                "description": "Return exactly: Hello, deterministic world",
                "dependencies": [],
                "estimated_duration": "1m"
            }
        ]
    }
    executor_selection = {
        "tool": "text_output",
        "params": {"text": "Hello, deterministic world"},
        "rationale": "Deterministic output"
    }

    def mock_llm_response(request):
        if "Task Step:" in request.content.decode("utf-8"):
            return Response(200, json={"choices": [{"message": {"content": json.dumps(executor_selection)}}]})
        return Response(200, json={"choices": [{"message": {"content": json.dumps(planner_plan)}}]})

    with respx.mock(base_url="http://mock-llm/v1") as respx_mock:
        respx_mock.post("/chat/completions").mock(side_effect=mock_llm_response)

        task_id = await controller.run_task(goal)

    assert task_id.startswith("task_")
    assert controller.state.value == "COMPLETED"

    archive_files = list((tmp_path / "tasks" / "archive").rglob(f"*{task_id}*"))
    assert len(archive_files) == 1

    active_files = list((tmp_path / "tasks").glob("task_*.json"))
    assert active_files == []

    with open(archive_files[0], "r") as f:
        saved_state = json.load(f)
        assert saved_state["status"] == "COMPLETED"
        assert saved_state["completed_steps"][0]["tool_name"] == "text_output"
        assert saved_state["completed_steps"][0]["artifact"] == "Hello, deterministic world"