"""
Minimal voice execution runtime for JARVISv4.
Provides subprocess-based execution of whisper (STT) and piper (TTS) binaries.
"""

import subprocess
import time
import os
from typing import Dict, Any, List, Optional
from datetime import datetime

def _run_command(command: List[str], timeout: int = 30) -> Dict[str, Any]:
    """
    Execute a command and return structured result.

    Args:
        command: Command and arguments as list
        timeout: Maximum execution time in seconds

    Returns:
        Structured result dictionary with execution details
    """
    start_time = time.time()

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=False
        )

        duration_ms = (time.time() - start_time) * 1000

        return {
            "success": result.returncode == 0,
            "command": command,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "return_code": result.returncode,
            "duration_ms": duration_ms,
            "timestamp": datetime.now().isoformat()
        }

    except subprocess.TimeoutExpired as e:
        duration_ms = (time.time() - start_time) * 1000
        return {
            "success": False,
            "command": command,
            "stdout": "",
            "stderr": f"Command timed out after {timeout} seconds: {str(e)}",
            "return_code": -1,
            "duration_ms": duration_ms,
            "timestamp": datetime.now().isoformat()
        }

    except FileNotFoundError as e:
        duration_ms = (time.time() - start_time) * 1000
        return {
            "success": False,
            "command": command,
            "stdout": "",
            "stderr": f"Command not found: {str(e)}",
            "return_code": -2,
            "duration_ms": duration_ms,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        return {
            "success": False,
            "command": command,
            "stdout": "",
            "stderr": f"Unexpected error: {str(e)}",
            "return_code": -3,
            "duration_ms": duration_ms,
            "timestamp": datetime.now().isoformat()
        }

def run_stt(audio_file_path: str, model: str = "base", **kwargs) -> Dict[str, Any]:
    """
    Execute Speech-to-Text using whisper binary.

    Args:
        audio_file_path: Path to audio file
        model: Whisper model size (base, small, medium, large)
        **kwargs: Additional whisper arguments (language, etc.)

    Returns:
        Structured result dictionary
    """
    if not os.path.exists(audio_file_path):
        return {
            "success": False,
            "command": [],
            "stdout": "",
            "stderr": f"Audio file not found: {audio_file_path}",
            "return_code": -4,
            "duration_ms": 0.0,
            "timestamp": datetime.now().isoformat()
        }

    # Build whisper command
    command = ["whisper", audio_file_path, "--model", model]

    # Add additional arguments
    for key, value in kwargs.items():
        if value is not None and value != "":
            command.extend([f"--{key}", str(value)])

    return _run_command(command)

def run_tts(text: str, voice: str = "default", output_file: Optional[str] = None, **kwargs) -> Dict[str, Any]:
    """
    Execute Text-to-Speech using piper binary.

    Args:
        text: Text to synthesize
        voice: Voice model to use
        output_file: Optional output file path
        **kwargs: Additional piper arguments

    Returns:
        Structured result dictionary
    """
    # Build piper command
    command = ["piper", "--model", voice, "--output_file", output_file] if output_file else ["piper", "--model", voice]

    # For B1, we only support --help execution
    if text != "--help":
        return {
            "success": False,
            "command": [],
            "stdout": "",
            "stderr": "TTS real execution deferred to future phase",
            "return_code": -5,
            "duration_ms": 0.0,
            "timestamp": datetime.now().isoformat()
        }

    command = ["piper", text]

    return _run_command(command)