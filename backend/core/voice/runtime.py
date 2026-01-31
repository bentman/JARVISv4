"""
Minimal voice execution runtime for JARVISv4.
Provides subprocess-based execution of whisper (STT) and piper (TTS) binaries.
"""

import subprocess
import time
import os
import glob
from typing import Dict, Any, List, Optional, Tuple
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


def _resolve_openwakeword_models(model_base: str) -> Tuple[Dict[str, List[str]], Dict[str, bool]]:
    oww_dir = os.path.join(model_base, "openwakeword")
    required_patterns = {
        "wakeword": [
            os.path.join(oww_dir, "alexa*.onnx"),
            os.path.join(oww_dir, "alexa*.tflite"),
        ],
        "melspectrogram": [
            os.path.join(oww_dir, "melspectrogram*.onnx"),
            os.path.join(oww_dir, "melspectrogram*.tflite"),
        ],
        "embedding_model": [
            os.path.join(oww_dir, "embedding_model*.onnx"),
            os.path.join(oww_dir, "embedding_model*.tflite"),
        ],
    }

    presence = {}
    for key, patterns in required_patterns.items():
        presence[key] = any(glob.glob(pattern) for pattern in patterns)

    return required_patterns, presence


_OWW_STARTUP_PROVISIONED = False


def _provision_openwakeword_models(model_base: str) -> Dict[str, Any]:
    oww_dir = os.path.join(model_base, "openwakeword")
    try:
        os.makedirs(oww_dir, exist_ok=True)
    except OSError as exc:
        if "Read-only file system" in str(exc):
            return {
                "provision_attempted": True,
                "provisioned": False,
                "provision_error": f"Models directory is read-only: {oww_dir}",
            }
        return {
            "provision_attempted": True,
            "provisioned": False,
            "provision_error": f"Failed to create models directory: {exc}",
        }

    try:
        import openwakeword.utils
    except Exception as exc:
        return {
            "provision_attempted": True,
            "provisioned": False,
            "provision_error": f"openWakeWord utils not available: {exc}",
        }

    try:
        openwakeword.utils.download_models(
            model_names=["alexa", "melspectrogram", "embedding_model"],
            target_directory=oww_dir,
        )
    except Exception as exc:
        return {
            "provision_attempted": True,
            "provisioned": False,
            "provision_error": f"Failed to provision openWakeWord models: {exc}",
        }

    _, presence = _resolve_openwakeword_models(model_base)
    provisioned = all(presence.values())
    return {
        "provision_attempted": True,
        "provisioned": provisioned,
        "provision_error": None if provisioned else "Provisioning completed but models are missing",
    }


def run_wake_word(audio_file_path: str, threshold: float = 0.5) -> Dict[str, Any]:
    """
    Detect wake word using openWakeWord models with deterministic artifacts.

    Args:
        audio_file_path: Path to audio file (WAV, PCM 16-bit preferred).
        threshold: Detection threshold (default 0.5).

    Returns:
        Structured result dictionary
    """
    start_time = time.time()
    settings = load_settings()
    policy = settings.model_provisioning_policy

    model_base = os.environ.get("MODEL_PATH", "/models")
    required_patterns, presence = _resolve_openwakeword_models(model_base)
    model_found = all(presence.values())
    model_error = None if model_found else "OpenWakeWord model files not found under MODEL_PATH"
    provisioning_details: Optional[Dict[str, Any]] = None

    artifacts_base = {
        "detected": False,
        "scores": {},
        "threshold": threshold,
        "model_base_path": model_base,
        "model_required": required_patterns,
        "model_found": model_found,
        "model_error": model_error,
        "provisioning_policy": policy,
    }

    if not os.path.exists(audio_file_path):
        return {
            "success": False,
            "command": [],
            "stdout": "",
            "stderr": f"Audio file not found: {audio_file_path}",
            "return_code": -4,
            "duration_ms": 0.0,
            "timestamp": datetime.now().isoformat(),
            "mode": "wake_word",
            "input": {
                "audio_file_path": audio_file_path,
                "threshold": threshold,
            },
            "artifacts": artifacts_base,
        }

    try:
        from openwakeword.model import Model as OWWModel
        import numpy as np
    except Exception as exc:
        return {
            "success": False,
            "command": [],
            "stdout": "",
            "stderr": f"openWakeWord not available: {exc}",
            "return_code": -7,
            "duration_ms": 0.0,
            "timestamp": datetime.now().isoformat(),
            "mode": "wake_word",
            "input": {
                "audio_file_path": audio_file_path,
                "threshold": threshold,
            },
            "artifacts": artifacts_base,
        }

    global _OWW_STARTUP_PROVISIONED
    if not model_found and policy in ("on_demand", "startup"):
        if policy == "startup" and _OWW_STARTUP_PROVISIONED:
            provisioning_details = None
        else:
            provisioning_details = _provision_openwakeword_models(model_base)
            if policy == "startup":
                _OWW_STARTUP_PROVISIONED = True
            required_patterns, presence = _resolve_openwakeword_models(model_base)
            model_found = all(presence.values())
            model_error = None if model_found else "OpenWakeWord model files not found under MODEL_PATH"
            artifacts_base["model_required"] = required_patterns
            artifacts_base["model_found"] = model_found
            artifacts_base["model_error"] = model_error

    if provisioning_details:
        artifacts_base.update(provisioning_details)

    if not model_found:
        return {
            "success": False,
            "command": [],
            "stdout": "",
            "stderr": model_error,
            "return_code": -6,
            "duration_ms": 0.0,
            "timestamp": datetime.now().isoformat(),
            "mode": "wake_word",
            "input": {
                "audio_file_path": audio_file_path,
                "threshold": threshold,
            },
            "artifacts": artifacts_base,
        }

    try:
        import wave

        with wave.open(audio_file_path, "rb") as wav_file:
            n_channels = wav_file.getnchannels()
            sampwidth = wav_file.getsampwidth()
            framerate = wav_file.getframerate()
            frames = wav_file.getnframes()
            pcm_bytes = wav_file.readframes(frames)

        if sampwidth != 2:
            raise ValueError("Unsupported sample width; expected 16-bit PCM")

        pcm = np.frombuffer(pcm_bytes, dtype=np.int16)
        if n_channels > 1:
            pcm = pcm.reshape(-1, n_channels).mean(axis=1).astype(np.int16)

        target_sr = 16000
        if framerate != target_sr:
            x_old = np.linspace(0, 1, num=len(pcm), endpoint=False)
            x_new = np.linspace(0, 1, num=int(len(pcm) * target_sr / framerate), endpoint=False)
            pcm = np.interp(x_new, x_old, pcm).astype(np.int16)

        audio = (pcm.astype(np.float32) / 32768.0).reshape(1, -1)

        oww_dir = os.path.join(model_base, "openwakeword")
        model_files = glob.glob(os.path.join(oww_dir, "*.onnx"))
        inference_framework = "onnx"
        if not model_files:
            model_files = glob.glob(os.path.join(oww_dir, "*.tflite"))
            inference_framework = "tflite"

        melspec_path = next(iter(glob.glob(os.path.join(oww_dir, "melspectrogram*.onnx"))), None)
        embedding_path = next(iter(glob.glob(os.path.join(oww_dir, "embedding_model*.onnx"))), None)

        wake_model = OWWModel(
            wakeword_models=model_files,
            inference_framework=inference_framework,
            melspec_model_path=melspec_path,
            embedding_model_path=embedding_path,
        )

        scores_raw = wake_model.predict(audio)
        scores = {}
        for key, score in scores_raw.items():
            if isinstance(score, (list, tuple, np.ndarray)):
                scores[key] = float(np.max(score))
            else:
                scores[key] = float(score)

        detected = any(val >= threshold for val in scores.values()) if scores else False
        duration_ms = (time.time() - start_time) * 1000

        return {
            "success": True,
            "command": [],
            "stdout": "",
            "stderr": "",
            "return_code": 0,
            "duration_ms": duration_ms,
            "timestamp": datetime.now().isoformat(),
            "mode": "wake_word",
            "input": {
                "audio_file_path": audio_file_path,
                "threshold": threshold,
            },
            "artifacts": {
                **artifacts_base,
                "detected": detected,
                "scores": scores,
            },
        }
    except Exception as exc:
        duration_ms = (time.time() - start_time) * 1000
        return {
            "success": False,
            "command": [],
            "stdout": "",
            "stderr": f"Wake word detection failed: {exc}",
            "return_code": -8,
            "duration_ms": duration_ms,
            "timestamp": datetime.now().isoformat(),
            "mode": "wake_word",
            "input": {
                "audio_file_path": audio_file_path,
                "threshold": threshold,
            },
            "artifacts": artifacts_base,
        }
