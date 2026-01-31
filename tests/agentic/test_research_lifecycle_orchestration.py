import json
import pytest

from backend.core.controller import ECFController


@pytest.mark.asyncio
async def test_research_lifecycle_orchestration(tmp_path, monkeypatch):
    tasks_path = tmp_path / "tasks"
    monkeypatch.setenv("WORKING_STORAGE_PATH", str(tasks_path))
    monkeypatch.setenv("LLM_BASE_URL", "http://mock-llm/v1")
    monkeypatch.setenv("LLM_MODEL", "test-model")

    controller = ECFController()

    task_id = await controller.run_research_lifecycle(
        query="deterministic research query",
        synthesis_text="deterministic synthesis",
        provider="duckduckgo",
        max_results=2
    )

    archive_files = list((tasks_path / "archive").rglob(f"*{task_id}*completed.json"))
    assert len(archive_files) == 1, "Research lifecycle should archive as COMPLETED"

    with open(archive_files[0], "r") as f:
        state = json.load(f)

    completed = state.get("completed_steps", [])
    assert len(completed) == 2

    search_step = completed[0]
    assert search_step["tool_name"] == "web_search"
    assert search_step["tool_params"] == {
        "query": "deterministic research query",
        "provider": "duckduckgo",
        "max_results": 2
    }
    search_artifact = search_step["artifact"]
    assert search_artifact["query"] == "deterministic research query"
    assert search_artifact["provider"] == "duckduckgo"
    assert search_artifact["max_results"] == 2
    assert "result" in search_artifact

    synth_step = completed[1]
    assert synth_step["tool_name"] == "text_output"
    assert synth_step["artifact"] == "deterministic synthesis"

    session_id = f"research_session_{task_id}"
    session_path = list((tasks_path / "archive").rglob(f"{session_id}.json"))
    assert len(session_path) == 1, "ResearchSession artifact should be archived"

    with open(session_path[0], "r") as f:
        session = json.load(f)

    assert session["session_id"] == session_id
    assert session["task_id"] == task_id
    assert session["step_order"] == ["web_search", "text_output"]
    for step_key, entry in session["step_artifacts"].items():
        assert step_key in session["step_order"]
        assert "archive_path" in entry
        assert "completed_step_index" in entry

    replay_result = controller.replay_research_session(session_id)
    assert replay_result["status"] == "COMPLETED"
    assert replay_result["validated_steps"] == len(session["step_order"])