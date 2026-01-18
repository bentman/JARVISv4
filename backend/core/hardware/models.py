"""
Hardware-related data models for JARVISv4
"""
from typing import List
from pydantic import BaseModel

class HardwareState(BaseModel):
    """Current state of system hardware resources"""
    gpu_usage: float
    memory_available_gb: float
    cpu_usage: float
    available_tiers: List[str]
    current_load: float
