import json
import os
import pytest

from backend.core.controller import ECFController


@pytest.mark.asyncio
async def test_voice_lifecycle_orchestration(tmp_path, monkeypatch):
    """
    Validate the deterministic end-to-end voice lifecycle:
    wake_word -> capture -> stt -> agent execution -> tts -> archive.
    """
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

    archive_files = list((tasks_path / "archive").rglob(f"*{task_id}*completed.json"))
    assert len(archive_files) == 1, "Voice lifecycle should archive as COMPLETED"

    with open(archive_files[0], "r") as f:
        state = json.load(f)

    completed = state.get("completed_steps", [])
    assert len(completed) == 5, "Voice lifecycle should record 5 completed steps"

    wake_step = completed[0]
    assert wake_step["tool_name"] == "voice_wake_word"
    assert wake_step["tool_params"]["audio_file_path"] == audio_path
    assert "mode" in wake_step["artifact"]

    capture_step = completed[1]
    assert capture_step["tool_name"] == "text_output"
    assert capture_step["artifact"] == audio_path

    stt_step = completed[2]
    assert stt_step["tool_name"] == "voice_stt"
    assert stt_step["tool_params"]["audio_file_path"] == audio_path

    agent_step = completed[3]
    assert agent_step["tool_name"] == "text_output"
    assert agent_step["artifact"] == "voice_response"

    tts_step = completed[4]
    assert tts_step["tool_name"] == "voice_tts"
    assert tts_step["tool_params"]["text"] == "--help"