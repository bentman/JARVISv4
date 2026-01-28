"""
Unit tests for JARVISv4 voice tools.
Tests ToolRegistry integration and deterministic voice tool execution.
"""

import pytest
import os
from backend.tools.voice import VoiceSTTTool, VoiceTTSTool
from backend.tools.registry import ToolRegistry
from backend.tools.registry.registry import ToolParameterValidationError

class TestVoiceTools:
    """Test suite for voice tool integration."""

    def test_voice_stt_tool_registration(self):
        """Test that voice_stt tool can be registered and retrieved."""
        registry = ToolRegistry()
        tool = VoiceSTTTool()

        # Register the tool
        registry.register_tool(tool)

        # Verify registration
        assert "voice_stt" in registry.list_tools()
        assert registry.get_tool("voice_stt") is not None

        # Verify definition
        definition = tool.definition
        assert definition.name == "voice_stt"
        assert "audio_file_path" in definition.parameters["properties"]
        assert "model" in definition.parameters["properties"]
        assert "language" in definition.parameters["properties"]

    def test_voice_tts_tool_registration(self):
        """Test that voice_tts tool can be registered and retrieved."""
        registry = ToolRegistry()
        tool = VoiceTTSTool()

        # Register the tool
        registry.register_tool(tool)

        # Verify registration
        assert "voice_tts" in registry.list_tools()
        assert registry.get_tool("voice_tts") is not None

        # Verify definition
        definition = tool.definition
        assert definition.name == "voice_tts"
        assert "text" in definition.parameters["properties"]
        assert "voice" in definition.parameters["properties"]

    @pytest.mark.asyncio
    async def test_voice_stt_execution_with_test_wav(self):
        """Test voice_stt tool execution with existing test.wav fixture."""
        test_wav_path = os.path.join("tests", "test.wav")
        if not os.path.exists(test_wav_path):
            pytest.skip("test.wav fixture not available")

        tool = VoiceSTTTool()
        result = await tool.execute(audio_file_path=test_wav_path)

        # Verify structured result is returned
        assert isinstance(result, dict)
        assert "success" in result
        assert "command" in result
        assert "stdout" in result
        assert "stderr" in result
        assert "return_code" in result
        assert "duration_ms" in result
        assert "timestamp" in result

    @pytest.mark.asyncio
    async def test_voice_tts_help_execution(self):
        """Test voice_tts tool execution with --help."""
        tool = VoiceTTSTool()
        result = await tool.execute(text="--help")

        # Verify structured result is returned
        assert isinstance(result, dict)
        assert "success" in result
        assert "command" in result
        assert "stdout" in result
        assert "stderr" in result
        assert "return_code" in result
        assert "duration_ms" in result
        assert "timestamp" in result

    @pytest.mark.asyncio
    async def test_voice_stt_missing_file(self):
        """Test voice_stt tool with missing audio file returns structured error."""
        tool = VoiceSTTTool()
        result = await tool.execute(audio_file_path="nonexistent.wav")

        # Verify structured error result is returned (no exception)
        assert isinstance(result, dict)
        assert result["success"] is False
        assert result["return_code"] == -4  # File not found code from B1
        assert "Audio file not found" in result["stderr"]

    @pytest.mark.asyncio
    async def test_voice_stt_invalid_parameter(self):
        """Test voice_stt tool with invalid parameter returns structured error."""
        tool = VoiceSTTTool()
        result = await tool.execute(audio_file_path="")

        # Verify structured error result is returned (no exception)
        assert isinstance(result, dict)
        assert result["success"] is False
        assert result["return_code"] == -10  # Parameter validation code
        assert "must be a non-empty string" in result["stderr"]

    @pytest.mark.asyncio
    async def test_tool_registry_call_voice_stt(self):
        """Test voice_stt tool execution via ToolRegistry.call_tool()."""
        test_wav_path = os.path.join("tests", "test.wav")
        if not os.path.exists(test_wav_path):
            pytest.skip("test.wav fixture not available")

        registry = ToolRegistry()
        tool = VoiceSTTTool()
        registry.register_tool(tool)

        # Call through registry
        result = await registry.call_tool("voice_stt", audio_file_path=test_wav_path)

        # Verify structured result is returned
        assert isinstance(result, dict)
        assert "success" in result
        assert "command" in result
        assert "stdout" in result
        assert "stderr" in result
        assert "return_code" in result

    @pytest.mark.asyncio
    async def test_tool_registry_call_voice_tts(self):
        """Test voice_tts tool execution via ToolRegistry.call_tool()."""
        registry = ToolRegistry()
        tool = VoiceTTSTool()
        registry.register_tool(tool)

        # Call through registry
        result = await registry.call_tool("voice_tts", text="--help")

        # Verify structured result is returned
        assert isinstance(result, dict)
        assert "success" in result
        assert "command" in result
        assert "stdout" in result
        assert "stderr" in result
        assert "return_code" in result

    @pytest.mark.asyncio
    async def test_tool_registry_parameter_validation(self):
        """Test ToolRegistry parameter validation for voice tools."""
        registry = ToolRegistry()
        tool = VoiceSTTTool()
        registry.register_tool(tool)

        # Test missing required parameter
        with pytest.raises(ToolParameterValidationError):
            await registry.call_tool("voice_stt")

        # Test invalid parameter type
        with pytest.raises(ToolParameterValidationError):
            await registry.call_tool("voice_stt", audio_file_path=123)

    @pytest.mark.asyncio
    async def test_voice_tool_contract_compliance(self):
        """Test that voice tools return the required contract fields."""
        # Test STT Contract
        stt_tool = VoiceSTTTool()
        # We test with missing file to ensure contract holds even on failure
        stt_result = await stt_tool.execute(audio_file_path="nonexistent.wav")
        
        assert "mode" in stt_result
        assert stt_result["mode"] == "stt"
        assert "input" in stt_result
        assert stt_result["input"]["audio_file_path"] == "nonexistent.wav"
        assert "artifacts" in stt_result
        assert "transcript_text" in stt_result["artifacts"]
        assert stt_result["artifacts"]["transcript_text"] == ""
        
        # Test TTS Contract
        tts_tool = VoiceTTSTool()
        tts_result = await tts_tool.execute(text="--help")
        
        assert "mode" in tts_result
        assert tts_result["mode"] == "tts"
        assert "input" in tts_result
        assert tts_result["input"]["text"] == "--help"
        assert "artifacts" in tts_result
        assert "audio_path" in tts_result["artifacts"]
        assert tts_result["artifacts"]["audio_path"] is None

    @pytest.mark.asyncio
    async def test_voice_stt_model_missing_contract(self, monkeypatch, tmp_path):
        """Test voice_stt tool contract when model file is missing."""
        # Force model search path to a temp dir (guaranteed empty)
        monkeypatch.setenv("MODEL_PATH", str(tmp_path))
        
        test_wav_path = os.path.join("tests", "test.wav")
        if not os.path.exists(test_wav_path):
            pytest.skip("test.wav fixture not available")

        tool = VoiceSTTTool()
        # Use "base" model which should look for ggml-base.bin in tmp_path
        result = await tool.execute(audio_file_path=test_wav_path, model="base")

        assert result["success"] is False
        assert result["return_code"] == -6
        assert "Model file not found" in result["stderr"]
        
        # Verify contract fields
        assert "artifacts" in result
        artifacts = result["artifacts"]
        assert artifacts["model_base_path"] == str(tmp_path)
        assert artifacts["model_required"] == os.path.join(str(tmp_path), "ggml-base.bin")
        assert artifacts["model_found"] is False
        assert "Model file not found" in artifacts["model_error"]

    @pytest.mark.asyncio
    async def test_voice_tts_model_missing_contract(self, monkeypatch, tmp_path):
        """Test voice_tts tool contract when model file is missing (by ID resolution)."""
        monkeypatch.setenv("MODEL_PATH", str(tmp_path))
        
        tool = VoiceTTSTool()
        # Use "test-voice" which should resolve to {tmp_path}/piper/test-voice.onnx
        result = await tool.execute(text="Hello", voice="test-voice")
        
        assert result["success"] is False
        # Expect -5 (Deferred) instead of -6 (Model Missing) because B1 deferred behavior takes precedence
        assert result["return_code"] == -5
        assert "TTS real execution deferred" in result["stderr"]
        
        # Verify contract fields are still present and correct despite deferred execution
        assert "artifacts" in result
        artifacts = result["artifacts"]
        assert artifacts["model_base_path"] == str(tmp_path)
        # Check expected resolution path structure
        expected_path = os.path.join(str(tmp_path), "piper", "test-voice.onnx")
        assert artifacts["model_required"] == expected_path
        assert artifacts["model_found"] is False

    @pytest.mark.asyncio
    async def test_voice_tts_model_explicit_path_missing(self, monkeypatch, tmp_path):
        """Test voice_tts tool contract when explicit model path is missing."""
        monkeypatch.setenv("MODEL_PATH", str(tmp_path))
        
        explicit_path = os.path.join(str(tmp_path), "custom_model.onnx")
        
        tool = VoiceTTSTool()
        result = await tool.execute(text="Hello", voice=explicit_path)
        
        assert result["success"] is False
        # Expect -5 (Deferred) instead of -6 (Model Missing) because B1 deferred behavior takes precedence
        assert result["return_code"] == -5
        assert "TTS real execution deferred" in result["stderr"]
        
        assert "artifacts" in result
        artifacts = result["artifacts"]
        # When explicit path provided, it should be used as-is
        assert artifacts["model_required"] == explicit_path
        assert artifacts["model_found"] is False
