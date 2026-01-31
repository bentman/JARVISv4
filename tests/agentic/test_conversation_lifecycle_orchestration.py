import json
import pytest

from backend.core.controller import ECFController


@pytest.mark.asyncio
async def test_conversation_lifecycle_orchestration(tmp_path, monkeypatch):
    tasks_path = tmp_path / "tasks"
    monkeypatch.setenv("WORKING_STORAGE_PATH", str(tasks_path))
    monkeypatch.setenv("LLM_BASE_URL", "http://mock-llm/v1")
    monkeypatch.setenv("LLM_MODEL", "test-model")

    controller = ECFController()

    task_id = await controller.run_conversation_lifecycle([
        {"user": "hello", "assistant": "hi"},
        {"user": "status", "assistant": "all systems nominal"}
    ])

    archive_files = list((tasks_path / "archive").rglob(f"*{task_id}*completed.json"))
    assert len(archive_files) == 1, "Conversation lifecycle should archive as COMPLETED"

    with open(archive_files[0], "r") as f:
        state = json.load(f)

    completed = state.get("completed_steps", [])
    assert len(completed) == 4

    assert completed[0]["tool_name"] == "text_output"
    assert completed[0]["artifact"] == "hello"
    assert completed[1]["tool_name"] == "text_output"
    assert completed[1]["artifact"] == "hi"
    assert completed[2]["tool_name"] == "text_output"
    assert completed[2]["artifact"] == "status"
    assert completed[3]["tool_name"] == "text_output"
    assert completed[3]["artifact"] == "all systems nominal"

    session_id = f"conversation_session_{task_id}"
    session_path = list((tasks_path / "archive").rglob(f"{session_id}.json"))
    assert len(session_path) == 1, "ConversationSession artifact should be archived"

    with open(session_path[0], "r") as f:
        session = json.load(f)

    assert session["session_id"] == session_id
    assert session["task_id"] == task_id
    assert session["step_order"] == [
        "turn_0_user",
        "turn_0_assistant",
        "turn_1_user",
        "turn_1_assistant"
    ]
    for step_key, entry in session["step_artifacts"].items():
        assert step_key in session["step_order"]
        assert "archive_path" in entry
        assert "completed_step_index" in entry

    replay_result = controller.replay_conversation_session(session_id)
    assert replay_result["status"] == "COMPLETED"
    assert replay_result["validated_steps"] == len(session["step_order"])