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