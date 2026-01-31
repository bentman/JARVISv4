import json
import os
import pytest

from backend.core.controller import ECFController


@pytest.mark.asyncio
async def test_voice_session_creation_and_replay(tmp_path, monkeypatch):
    tasks_path = tmp_path / "tasks"
    monkeypatch.setenv("WORKING_STORAGE_PATH", str(tasks_path))
    monkeypatch.setenv("LLM_BASE_URL", "http://mock-llm/v1")
    monkeypatch.setenv("LLM_MODEL", "test-model")

    controller = ECFController()

    audio_path = os.path.join("tests", "test_alexa.wav")
    if not os.path.exists(audio_path):
        pytest.skip("test_alexa.wav fixture not available")

    task_id = await controller.run_voice_lifecycle(
        audio_file_path=audio_path,
        threshold=0.5,
        stt_model="base",
        tts_voice="default",
        agent_text="voice_response"
    )

    session_id = f"voice_session_{task_id}"
    session_path = list((tasks_path / "archive").rglob(f"{session_id}.json"))
    assert len(session_path) == 1, "VoiceSession artifact should be archived"

    with open(session_path[0], "r") as f:
        session = json.load(f)

    assert session["task_id"] == task_id
    assert session["session_id"] == session_id
    assert session["step_order"] == [
        "voice_wake_word",
        "voice_stt",
        "text_output",
        "voice_tts"
    ]
    for step_key, entry in session["step_artifacts"].items():
        assert step_key in session["step_order"]
        assert "archive_path" in entry
        assert "completed_step_index" in entry

    replay_result = controller.replay_voice_session(session_id)
    assert replay_result["status"] == "COMPLETED"
    assert replay_result["validated_steps"] == len(session["step_order"])

    invalid_session = dict(session)
    invalid_session["session_id"] = f"{session_id}_invalid"
    invalid_session["step_order"] = list(session["step_order"])
    invalid_session["step_order"][0] = "voice_stt"
    invalid_session["step_artifacts"] = dict(session["step_artifacts"])
    invalid_session["step_artifacts"]["voice_stt"] = dict(
        invalid_session["step_artifacts"].pop("voice_wake_word")
    )

    invalid_path = session_path[0].with_name(f"{invalid_session['session_id']}.json")
    with open(invalid_path, "w") as f:
        json.dump(invalid_session, f, indent=2)

    mismatch_result = controller.replay_voice_session(invalid_session["session_id"])
    assert mismatch_result["status"] == "FAILED"
    assert any("Tool mismatch" in error for error in mismatch_result["errors"])

    out_of_range_session = dict(session)
    out_of_range_session["session_id"] = f"{session_id}_out_of_range"
    out_of_range_session["step_artifacts"] = dict(session["step_artifacts"])
    out_of_range_session["step_artifacts"]["voice_wake_word"] = dict(
        out_of_range_session["step_artifacts"]["voice_wake_word"]
    )
    out_of_range_session["step_artifacts"]["voice_wake_word"]["completed_step_index"] = 999

    out_of_range_path = session_path[0].with_name(
        f"{out_of_range_session['session_id']}.json"
    )
    with open(out_of_range_path, "w") as f:
        json.dump(out_of_range_session, f, indent=2)

    out_of_range_result = controller.replay_voice_session(out_of_range_session["session_id"])
    assert out_of_range_result["status"] == "FAILED"
    assert any("Completed step index invalid" in error for error in out_of_range_result["errors"])