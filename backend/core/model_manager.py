"""
Minimal model provisioning helper for JARVISv4.
Provides deterministic, policy-gated download behavior for voice models.
"""

from __future__ import annotations

import logging
import os
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ModelProfile:
    model_id: str
    filename: str


class ModelProvisioningError(RuntimeError):
    """Deterministic error for model provisioning failures."""


class ModelManager:
    """
    Minimal model manager for STT/TTS provisioning.
    Supports download_recommended_model("stt"|"tts") with deterministic failures.
    """

    def __init__(self, models_dir: Optional[Path] = None) -> None:
        target_dir = models_dir or Path(os.environ.get("MODEL_PATH", "/models"))
        self.models_dir = target_dir
        try:
            self.models_dir.mkdir(exist_ok=True, parents=True)
        except OSError as exc:
            if "Read-only file system" not in str(exc):
                raise
            logger.info("Models directory is read-only; skipping creation: %s", self.models_dir)

        self._download_locks: dict[str, threading.Lock] = {}

    def _get_profile(self, tier: str) -> ModelProfile:
        profiles = {
            "stt": ModelProfile(
                model_id="ggerganov/whisper.cpp",
                filename="ggml-base.bin",
            ),
            "tts": ModelProfile(
                model_id="rhasspy/piper-voices",
                filename="en/en_US/lessac/medium/en_US-lessac-medium.onnx",
            ),
            "tts-config": ModelProfile(
                model_id="rhasspy/piper-voices",
                filename="en/en_US/lessac/medium/en_US-lessac-medium.onnx.json",
            ),
        }
        if tier not in profiles:
            raise ModelProvisioningError(f"Unknown model tier: {tier}")
        return profiles[tier]

    def download_recommended_model(self, tier: str) -> Optional[Path]:
        profile = self._get_profile(tier)
        model_path = self.models_dir / profile.filename

        if model_path.exists():
            return model_path

        lock = self._download_locks.setdefault(profile.filename, threading.Lock())
        with lock:
            if model_path.exists():
                return model_path

            try:
                try:
                    from huggingface_hub import hf_hub_download
                except ImportError as exc:
                    raise ModelProvisioningError(
                        "huggingface_hub is not installed; cannot download models"
                    ) from exc

                downloaded = hf_hub_download(
                    repo_id=profile.model_id,
                    filename=profile.filename,
                    local_dir=str(self.models_dir),
                    local_dir_use_symlinks=False,
                )
            except Exception as exc:
                raise ModelProvisioningError(
                    f"Failed to download model {profile.filename}: {exc}"
                ) from exc

            downloaded_path = Path(downloaded)
            if not downloaded_path.exists():
                raise ModelProvisioningError(
                    f"Downloaded model missing on disk: {downloaded_path}"
                )

            return downloaded_path


model_manager = ModelManager()