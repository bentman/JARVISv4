import pytest

from backend.core.config.settings import load_settings
from backend.core.controller import ECFController
from backend.main import run_list_tasks
from backend.memory.working_state import WorkingStateManager


@pytest.mark.asyncio
async def test_task_supervision_list_tasks(tmp_path, monkeypatch, capsys):
    tasks_path = tmp_path / "tasks"
    monkeypatch.setenv("WORKING_STORAGE_PATH", str(tasks_path))

    state_manager = WorkingStateManager(tasks_path)
    active_task_id = state_manager.create_task({
        "goal": "Active task",
        "domain": "general",
        "constraints": [],
        "next_steps": []
    })
    archived_task_id = state_manager.create_task({
        "goal": "Archived task",
        "domain": "general",
        "constraints": [],
        "next_steps": []
    })
    state_manager.update_task(archived_task_id, {"status": "COMPLETED"})
    state_manager.archive_task(archived_task_id, reason="completed")

    controller = ECFController()
    summaries = controller.list_task_summaries()
    await controller.llm.close()

    assert len(summaries) >= 2

    lifecycle_map = {summary["task_id"]: summary["lifecycle"] for summary in summaries}
    assert lifecycle_map[active_task_id] == "ACTIVE"
    assert lifecycle_map[archived_task_id] == "ARCHIVED"

    ordered_ids = [summary["task_id"] for summary in summaries]
    expected_order = sorted([active_task_id]) + sorted([archived_task_id])
    assert ordered_ids == expected_order

    settings = load_settings(override_environ=True)
    count = await run_list_tasks(settings)
    output = capsys.readouterr().out
    assert count == len(summaries)
    assert "TASK " in output