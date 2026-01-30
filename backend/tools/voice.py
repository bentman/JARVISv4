"""
Voice tools for JARVISv4.
Provides ECF-facing voice execution tools that wrap the Phase B1 voice runtime.
"""

import os
from typing import Any, Dict
from backend.tools.base import BaseTool, ToolDefinition
from backend.core.voice.runtime import run_stt, run_tts, run_wake_word

class VoiceSTTTool(BaseTool):
    """
    Speech-to-Text tool that wraps the Phase B1 voice runtime.
    Executes whisper binary for audio transcription.
    """

    def __init__(self):
        self._definition = ToolDefinition(
            name="voice_stt",
            description="Convert speech to text using whisper (requires audio file path).",
            parameters={
                "type": "object",
                "properties": {
                    "audio_file_path": {
                        "type": "string",
                        "description": "Path to the audio file to transcribe"
                    },
                    "model": {
                        "type": "string",
                        "description": "Whisper model size (base, small, medium, large)",
                        "default": "base"
                    },
                    "language": {
                        "type": "string",
                        "description": "Optional language hint for transcription",
                        "default": None
                    }
                },
                "required": ["audio_file_path"]
            }
        )

    @property
    def definition(self) -> ToolDefinition:
        return self._definition

    async def execute(self, **kwargs) -> Dict[str, Any]:
        """
        Execute STT using the Phase B1 voice runtime.
        Returns structured result dict verbatim (including failures).
        """
        audio_file_path = kwargs.get("audio_file_path")
        model = kwargs.get("model", "base")
        language = kwargs.get("language")

        # Minimal parameter validation that can't be expressed in JSON schema
        if not audio_file_path or not isinstance(audio_file_path, str):
            return {
                "success": False,
                "command": [],
                "stdout": "",
                "stderr": "audio_file_path must be a non-empty string",
                "return_code": -10,
                "duration_ms": 0.0,
                "timestamp": __import__('datetime').datetime.now().isoformat()
            }

        # Pass additional parameters directly to runtime
        extra_params = {}
        if language:
            extra_params["language"] = language

        # Call Phase B1 runtime and return result verbatim
        return run_stt(audio_file_path, model, **extra_params)

class VoiceTTSTool(BaseTool):
    """
    Text-to-Speech tool that wraps the Phase B1 voice runtime.
    Executes piper binary for text synthesis (limited to --help in B2).
    """

    def __init__(self):
        self._definition = ToolDefinition(
            name="voice_tts",
            description="Convert text to speech using piper (B2: limited to --help execution).",
            parameters={
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "Text to synthesize (--help for B2 validation)"
                    },
                    "voice": {
                        "type": "string",
                        "description": "Voice model to use",
                        "default": "default"
                    }
                },
                "required": ["text"]
            }
        )

    @property
    def definition(self) -> ToolDefinition:
        return self._definition

    async def execute(self, **kwargs) -> Dict[str, Any]:
        """
        Execute TTS using the Phase B1 voice runtime.
        Returns structured result dict verbatim (including failures).
        """
        text = kwargs.get("text")
        voice = kwargs.get("voice", "default")

        # Minimal parameter validation that can't be expressed in JSON schema
        if not text or not isinstance(text, str):
            return {
                "success": False,
                "command": [],
                "stdout": "",
                "stderr": "text must be a non-empty string",
                "return_code": -10,
                "duration_ms": 0.0,
                "timestamp": __import__('datetime').datetime.now().isoformat()
            }

        # Call Phase B1 runtime and return result verbatim
        return run_tts(text, voice)


class VoiceWakeWordTool(BaseTool):
    """
    Wake word detection tool using openWakeWord.
    Returns deterministic artifact results.
    """

    def __init__(self):
        self._definition = ToolDefinition(
            name="voice_wake_word",
            description="Detect wake word using openWakeWord (requires audio file path).",
            parameters={
                "type": "object",
                "properties": {
                    "audio_file_path": {
                        "type": "string",
                        "description": "Path to the audio file to analyze"
                    },
                    "threshold": {
                        "type": "number",
                        "description": "Wake word detection threshold",
                        "default": 0.5
                    }
                },
                "required": ["audio_file_path"]
            }
        )

    @property
    def definition(self) -> ToolDefinition:
        return self._definition

    async def execute(self, **kwargs) -> Dict[str, Any]:
        """
        Execute wake word detection via runtime.
        Returns structured result dict verbatim (including failures).
        """
        audio_file_path = kwargs.get("audio_file_path")
        threshold = kwargs.get("threshold", 0.5)

        if not audio_file_path or not isinstance(audio_file_path, str):
            return {
                "success": False,
                "command": [],
                "stdout": "",
                "stderr": "audio_file_path must be a non-empty string",
                "return_code": -10,
                "duration_ms": 0.0,
                "timestamp": __import__('datetime').datetime.now().isoformat()
            }

        return run_wake_word(audio_file_path, threshold)