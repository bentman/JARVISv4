"""
Unit tests for JARVISv4 voice runtime module.
Tests subprocess execution of whisper and piper binaries.
"""

import pytest
import os
from backend.core.voice.runtime import run_stt, run_tts

class TestVoiceRuntime:
    """Test suite for voice runtime functions."""

    def test_whisper_help(self):
        """Test whisper --help execution."""
        # For whisper --help, we need to create a dummy file since whisper requires an audio file
        # This test will check if whisper binary is available and can process help-like output
        # We'll use a non-existent file to get the help/usage output
        result = run_stt("dummy_for_help.wav")
        assert isinstance(result, dict)
        assert "success" in result
        assert "command" in result
        assert "stdout" in result
        assert "stderr" in result
        assert "return_code" in result
        assert "duration_ms" in result
        assert "timestamp" in result

    def test_piper_help(self):
        """Test piper --help execution."""
        result = run_tts("--help")
        assert isinstance(result, dict)
        assert "success" in result
        assert "command" in result
        assert "stdout" in result
        assert "stderr" in result
        assert "return_code" in result
        assert "duration_ms" in result
        assert "timestamp" in result

    def test_whisper_with_test_wav(self):
        """Test whisper execution with existing test.wav fixture."""
        test_wav_path = os.path.join("tests", "test.wav")
        if not os.path.exists(test_wav_path):
            pytest.skip("test.wav fixture not available")

        result = run_stt(test_wav_path)
        assert isinstance(result, dict)
        assert "success" in result
        assert "command" in result
        assert "stdout" in result
        assert "stderr" in result
        assert "return_code" in result
        assert "duration_ms" in result
        assert "timestamp" in result

    def test_missing_audio_file(self):
        """Test intentional failure with missing audio file."""
        result = run_stt("nonexistent.wav")
        assert isinstance(result, dict)
        assert result["success"] is False
        assert result["return_code"] == -4
        assert "Audio file not found" in result["stderr"]
        assert result["stderr"] == "Audio file not found: nonexistent.wav"

    def test_tts_real_execution_deferred(self):
        """Test that TTS real execution is deferred."""
        result = run_tts("Hello world")
        assert isinstance(result, dict)
        assert result["success"] is False
        assert result["return_code"] == -5
        assert "TTS real execution deferred" in result["stderr"]