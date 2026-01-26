"""
JARVISv4 Voice Runtime Package
Provides subprocess-based execution of voice binaries.
"""

from .runtime import run_stt, run_tts

__all__ = ["run_stt", "run_tts"]