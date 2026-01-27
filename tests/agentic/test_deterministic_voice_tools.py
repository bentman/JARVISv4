import pytest
import json
import os
from backend.core.controller import ECFController
from backend.core.llm.base import BaseLLMProvider
from backend.tools.voice import VoiceSTTTool, VoiceTTSTool

class FakeVoiceLLM(BaseLLMProvider):
    async def generate(self, prompt: str, **kwargs) -> str:
        # Check specific task step instructions to determine deterministic tool choice
        if "Execute voice STT" in prompt:
             return json.dumps({
                "tool": "voice_stt",
                "params": {"audio_file_path": "tests/test.wav"},
                "rationale": "STT requested"
            })
        if "Execute voice TTS" in prompt:
             return json.dumps({
                "tool": "voice_tts",
                "params": {"text": "--help"},
                "rationale": "TTS help requested"
            })
        # Default or fallback
        return json.dumps({"tool": "none", "rationale": "No match"})
    
    async def close(self):
        pass

@pytest.mark.asyncio
async def test_deterministic_voice_execution(tmp_path, monkeypatch):
    """
    Verifies that voice tools can be invoked via the standard execution path
    using a deterministic plan and fake LLM (no respx/network mocking).
    """
    # Setup environment
    tasks_path = tmp_path / "tasks"
    monkeypatch.setenv("WORKING_STORAGE_PATH", str(tasks_path))
    monkeypatch.setenv("LLM_BASE_URL", "http://mock-llm/v1") 
    monkeypatch.setenv("LLM_MODEL", "test-model")

    # Initialize Controller
    controller = ECFController()
    
    # Assert registration
    tool_names = [t.definition.name for t in controller.registry._tools.values()]
    assert "voice_stt" in tool_names, "voice_stt should be registered"
    assert "voice_tts" in tool_names, "voice_tts should be registered"

    # Inject Fake LLM to bypass actual inference and HTTP mocks
    fake_llm = FakeVoiceLLM()
    controller.llm = fake_llm
    controller.executor.llm = fake_llm # Ensure executor uses the fake too

    # Inject Task with Deterministic Plan
    state_manager = controller.state_manager
    task_id = state_manager.create_task({
        "goal": "Test voice tools",
        "domain": "test",
        "constraints": [],
        "next_steps": [
            {
                "description": "Execute voice STT on tests/test.wav"
            },
            {
                "description": "Execute voice TTS with help"
            }
        ]
    })

    # Run Execution (Resume)
    # This invokes controller._execute_remaining_steps -> executor.execute_step -> fake_llm.generate -> registry.call_tool
    await controller.resume_task(task_id)

    # Verify Results in Archived State
    archive_files = list((tasks_path / "archive").rglob(f"*{task_id}*completed.json"))
    assert len(archive_files) == 1, "Task should be archived as COMPLETED"

    with open(archive_files[0], "r") as f:
        state = json.load(f)

    # Check that steps were completed and tools recorded
    completed = state.get("completed_steps", [])
    assert len(completed) == 2, "Should have 2 completed steps"
    
    # Step 1: STT
    stt_step = completed[0]
    assert stt_step["tool_name"] == "voice_stt"
    assert stt_step["tool_params"]["audio_file_path"] == "tests/test.wav"
    # Even if binaries are missing, the tool returns a dict result
    stt_artifact = stt_step.get("artifact")
    assert stt_artifact is not None
    
    # Step 2: TTS
    tts_step = completed[1]
    assert tts_step["tool_name"] == "voice_tts"
    assert tts_step["tool_params"]["text"] == "--help"
    tts_artifact = tts_step.get("artifact")
    assert tts_artifact is not None


