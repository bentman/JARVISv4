"""
Minimal voice execution runtime for JARVISv4.
Provides subprocess-based execution of whisper (STT) and piper (TTS) binaries.
"""

import subprocess
import time
import os
from typing import Dict, Any, List, Optional
from datetime import datetime

from backend.core.config.settings import load_settings
from backend.core.model_manager import ModelProvisioningError, model_manager

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
            "timestamp": datetime.now().isoformat(),
            "mode": "stt",
            "input": {
                "audio_file_path": audio_file_path,
                "model": model,
                "language": kwargs.get("language")
            },
            "artifacts": {
                "transcript_text": "",
                "transcript_path": None
            }
        }

    # Check model presence (V4 Contract)
    model_base = os.environ.get("MODEL_PATH", "/models")
    model_filename = f"ggml-{model}.bin"
    model_required = os.path.join(model_base, model_filename)
    model_found = os.path.exists(model_required)

    settings = load_settings()
    policy = settings.model_provisioning_policy
    provisioning_fields = {
        "provisioning_policy": policy,
        "provision_attempted": False,
        "provisioned": False,
        "provision_error": None,
    }

    if not model_found and policy == "on_demand":
        provisioning_fields["provision_attempted"] = True
        try:
            model_manager.download_recommended_model("stt")
            model_found = os.path.exists(model_required)
            provisioning_fields["provisioned"] = model_found
        except ModelProvisioningError as exc:
            provisioning_fields["provision_error"] = str(exc)
    
    contract_extras = {
        "model_base_path": model_base,
        "model_required": model_required,
        "model_found": model_found,
        "model_error": None if model_found else f"Model file not found: {model_required}",
        **provisioning_fields
    }

    if not model_found:
        return {
            "success": False,
            "command": [],
            "stdout": "",
            "stderr": contract_extras["model_error"],
            "return_code": -6,
            "duration_ms": 0.0,
            "timestamp": datetime.now().isoformat(),
            "mode": "stt",
            "input": {
                "audio_file_path": audio_file_path,
                "model": model,
                "language": kwargs.get("language")
            },
            "artifacts": {
                "transcript_text": "",
                "transcript_path": None,
                **contract_extras
            }
        }

    # Build whisper command
    command = ["whisper", audio_file_path, "--model", model]

    # Add additional arguments
    for key, value in kwargs.items():
        if value is not None and value != "":
            command.extend([f"--{key}", str(value)])

    result = _run_command(command)
    
    # Enforce Phase B7 Contract
    result["mode"] = "stt"
    result["input"] = {
        "audio_file_path": audio_file_path,
        "model": model,
        "language": kwargs.get("language")
    }
    result["artifacts"] = {
        "transcript_text": "", # Deterministic empty string for now
        "transcript_path": None,
        **contract_extras
    }
    
    return result

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

    # Check model presence (V4 Contract for Piper)
    model_base = os.environ.get("MODEL_PATH", "/models")
    
    # Piper Resolution Logic:
    # 1. If 'voice' looks like an explicit path (exists, absolute, has separators, or .onnx extension), use it.
    # 2. Otherwise, resolve as {MODEL_PATH}/piper/{voice}.onnx
    is_explicit_path = (
        os.path.exists(voice) or 
        os.path.isabs(voice) or 
        os.sep in voice or 
        (os.altsep and os.altsep in voice) or
        voice.endswith(".onnx")
    )
    
    if is_explicit_path:
        model_required = voice
    else:
        model_required = os.path.join(model_base, "piper", f"{voice}.onnx")
    
    model_found = os.path.exists(model_required)

    settings = load_settings()
    policy = settings.model_provisioning_policy
    provisioning_fields = {
        "provisioning_policy": policy,
        "provision_attempted": False,
        "provisioned": False,
        "provision_error": None,
    }

    if not model_found and policy == "on_demand":
        provisioning_fields["provision_attempted"] = True
        try:
            model_manager.download_recommended_model("tts")
            model_found = os.path.exists(model_required)
            provisioning_fields["provisioned"] = model_found
        except ModelProvisioningError as exc:
            provisioning_fields["provision_error"] = str(exc)
    
    contract_extras = {
        "model_base_path": model_base,
        "model_required": model_required,
        "model_found": model_found,
        "model_error": None if model_found else f"Model file not found: {model_required}",
        **provisioning_fields
    }

    # For B1, we only support --help execution
    # This takes precedence over model check failures to preserve B1 regression behavior
    if text != "--help":
        return {
            "success": False,
            "command": [],
            "stdout": "",
            "stderr": "TTS real execution deferred to future phase",
            "return_code": -5,
            "duration_ms": 0.0,
            "timestamp": datetime.now().isoformat(),
            "mode": "tts",
            "input": {"text": text, "voice": voice},
            "artifacts": {
                "audio_path": None,
                **contract_extras
            }
        }

    # If we are here, text == "--help".
    # In help mode, we don't strictly need the model, but we should use the resolved path if we were to run real TTS.
    # However, 'piper --help' doesn't take model args usually, but let's stick to the contract logic.
    # Actually, B2/B3 established 'piper text' as the command pattern for help mode? 
    # Looking at B2 code: command = ["piper", text] where text="--help".
    # So model is not involved in the help command itself.
    
    command = ["piper", text]

    result = _run_command(command)
    
    # Enforce Phase B7/B9 Contract
    result["mode"] = "tts"
    result["input"] = {
        "text": text,
        "voice": voice
    }
    result["artifacts"] = {
        "audio_path": output_file,
        **contract_extras
    }
    
    return result
