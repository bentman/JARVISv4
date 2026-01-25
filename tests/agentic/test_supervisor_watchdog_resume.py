import json
import os
import time

import pytest
import respx
from httpx import Response

from backend.core.controller import ECFController
from backend.memory.working_state import WorkingStateManager


@pytest.mark.asyncio
async def test_supervisor_resumes_stalled_task(tmp_path, monkeypatch):
    tasks_path = tmp_path / "tasks"
    monkeypatch.setenv("WORKING_STORAGE_PATH", str(tasks_path))
    monkeypatch.setenv("LLM_BASE_URL", "http://mock-llm/v1")
    monkeypatch.setenv("LLM_MODEL", "test-model")

    state_manager = WorkingStateManager(tasks_path)
    task_id = state_manager.create_task({
        "goal": "Resume stalled task",
        "domain": "general",
        "constraints": [],
        "next_steps": [
            {
                "id": "1",
                "description": "Return exactly: Watchdog OK",
                "dependencies": [],
                "estimated_duration": "1m"
            }
        ]
    })

    task_file = tasks_path / f"{task_id}.json"
    old_timestamp = time.time() - 120
    os.utime(task_file, (old_timestamp, old_timestamp))

    controller = ECFController()
    resume_calls = {"count": 0}
    original_resume = controller.resume_task

    async def resume_spy(task_id: str, max_steps=None):
        resume_calls["count"] += 1
        return await original_resume(task_id, max_steps=max_steps)

    executor_selection = {
        "tool": "text_output",
        "params": {"text": "Watchdog OK"},
        "rationale": "Deterministic output"
    }

    async with respx.mock(base_url="http://mock-llm/v1") as respx_mock:
        respx_mock.post("/chat/completions").mock(return_value=Response(
            200,
            json={"choices": [{"message": {"content": json.dumps(executor_selection)}}]}
        ))

        controller.resume_task = resume_spy
        resumed = await controller.supervisor_resume_stalled_tasks(min_age_seconds=60)

    assert resumed == [task_id]
    assert resume_calls["count"] == 1

    archive_files = list((tasks_path / "archive").rglob(f"*{task_id}*completed.json"))
    assert len(archive_files) == 1
    assert not task_file.exists()

    with open(archive_files[0], "r") as archived:
        archived_state = json.load(archived)
        assert archived_state["status"] == "COMPLETED"
        assert archived_state["task_id"] == task_id