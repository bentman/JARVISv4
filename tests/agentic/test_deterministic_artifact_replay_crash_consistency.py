import json

import pytest
import respx
from httpx import Response

from backend.core.controller import ECFController
from backend.memory.working_state import WorkingStateManager


@pytest.mark.asyncio
async def test_replay_inflight_artifact_after_crash(tmp_path, monkeypatch):
    tasks_path = tmp_path / "tasks"
    monkeypatch.setenv("WORKING_STORAGE_PATH", str(tasks_path))
    monkeypatch.setenv("LLM_BASE_URL", "http://mock-llm/v1")
    monkeypatch.setenv("LLM_MODEL", "test-model")

    state_manager = WorkingStateManager(tasks_path)
    task_id = state_manager.create_task({
        "goal": "Deterministic artifact replay",
        "domain": "general",
        "constraints": [],
        "next_steps": [
            {
                "id": "1",
                "description": "Return exactly: Hello, deterministic world",
                "dependencies": [],
                "estimated_duration": "1m"
            }
        ]
    })

    task_state = state_manager.load_task(task_id)
    inflight_step = task_state["next_steps"][0]
    state_manager.update_task(task_id, {
        "current_step": {
            "index": 0,
            "description": inflight_step["description"]
        },
        "next_steps": task_state["next_steps"][1:]
    })

    controller = ECFController()

    executor_selection = {
        "tool": "text_output",
        "params": {"text": "Hello, deterministic world"},
        "rationale": "Deterministic output"
    }

    async with respx.mock(base_url="http://mock-llm/v1") as respx_mock:
        respx_mock.post("/chat/completions").mock(return_value=Response(
            200,
            json={"choices": [{"message": {"content": json.dumps(executor_selection)}}]}
        ))

        await controller.resume_task(task_id)

    archive_files = list((tasks_path / "archive").rglob(f"*{task_id}*completed.json"))
    assert len(archive_files) == 1

    active_files = list(tasks_path.glob("task_*.json"))
    assert active_files == []

    with open(archive_files[0], "r") as archived:
        archived_state = json.load(archived)

    assert archived_state["task_id"] == task_id
    assert archived_state["status"] == "COMPLETED"
    assert archived_state["completed_steps"][0]["artifact"] == "Hello, deterministic world"