"""
Hardware Detection Service for JARVISv4
Ported from v3 with focus on CPU/RAM/Disk baseline.
"""
import psutil
import platform
import logging
import threading
import time
from typing import Dict, Optional, List, Tuple, Callable, Any
from dataclasses import dataclass
from enum import Enum
from .models import HardwareState

logger = logging.getLogger(__name__)

class HardwareType(Enum):
    """Hardware acceleration types"""
    CPU_ONLY = "cpu_only"
    GPU_GENERAL = "gpu_general"
    GPU_CUDA = "gpu_cuda"
    NPU_APPLE = "npu_apple"
    NPU_QUALCOMM = "npu_qualcomm"
    NPU_INTEL = "npu_intel"

@dataclass
class MemoryAllocation:
    """Tracks memory allocation for a specific model/provider"""
    model_name: str
    provider: str
    allocated_mb: float
    max_mb: float
    timestamp: float

class ResourceManager:
    """Manages dynamic resource allocation and monitoring"""

    def __init__(self):
        self.allocations: Dict[str, MemoryAllocation] = {}
        self.lock = threading.Lock()
        self.memory_pressure_threshold = 0.85
        self.degradation_callbacks: List[Callable] = []

    def allocate_memory(self, model_name: str, provider: str, requested_mb: float) -> bool:
        """Attempt to allocate memory"""
        with self.lock:
            try:
                mem = psutil.virtual_memory()
                available_mb = (mem.available / (1024 * 1024))

                if available_mb < requested_mb:
                    logger.warning(f"Insufficient memory for {model_name}: requested {requested_mb}MB, available {available_mb}MB")
                    return False

                memory_pressure = (mem.total - mem.available) / mem.total
                if memory_pressure > self.memory_pressure_threshold:
                    logger.warning(f"High memory pressure ({memory_pressure:.1%}) detected")
                    self._trigger_degradation()

                allocation = MemoryAllocation(
                    model_name=model_name,
                    provider=provider,
                    allocated_mb=requested_mb,
                    max_mb=requested_mb,
                    timestamp=time.time()
                )
                self.allocations[f"{provider}_{model_name}"] = allocation
                logger.info(f"Allocated {requested_mb}MB for {model_name} on {provider}")
                return True
            except Exception as e:
                logger.error(f"Memory allocation failed: {e}")
                return False

    def deallocate_memory(self, model_name: str, provider: str):
        """Deallocate memory for a model"""
        with self.lock:
            key = f"{provider}_{model_name}"
            if key in self.allocations:
                allocation = self.allocations.pop(key)
                logger.info(f"Deallocated {allocation.allocated_mb}MB for {model_name} on {provider}")

    def check_resource_exhaustion(self) -> Optional[str]:
        """Check for resource exhaustion"""
        try:
            mem = psutil.virtual_memory()
            memory_pressure = (mem.total - mem.available) / mem.total
            if memory_pressure > 0.95: return "critical_memory_exhaustion"
            if memory_pressure > 0.90: return "high_memory_pressure"
            cpu_usage = psutil.cpu_percent(interval=1)
            if cpu_usage > 95: return "cpu_exhaustion"
            return None
        except Exception as e:
            logger.error(f"Resource exhaustion check failed: {e}")
            return None

    def _trigger_degradation(self):
        for callback in self.degradation_callbacks:
            try: callback()
            except Exception as e: logger.error(f"Degradation callback failed: {e}")

    def register_degradation_callback(self, callback: Callable):
        self.degradation_callbacks.append(callback)

class HardwareService:
    """Enhanced hardware detection and resource management"""

    def __init__(self):
        self._cpu_info = {}
        self._gpu_info = {}
        self._memory_info = {}
        self._accel_providers = []
        self._hardware_type = HardwareType.CPU_ONLY
        self.resource_manager = ResourceManager()
        self.degradation_active = False
        self._cuda_available = False
        self._npu_detected = False
        self._npu_type = None
        self.refresh_hardware_info()
        self.resource_manager.register_degradation_callback(self._handle_resource_degradation)

    def _handle_resource_degradation(self):
        if not self.degradation_active:
            logger.warning("Resource degradation triggered")
            self.degradation_active = True

    def detect_hardware_type(self) -> HardwareType:
        if self._is_cuda_available(): return HardwareType.GPU_CUDA
        npu_type = self._detect_npu_type()
        if npu_type: return npu_type
        if self._gpu_info:
            vendor = self._gpu_info.get("vendor", "unknown")
            if vendor in ["nvidia", "amd", "intel"]: return HardwareType.GPU_GENERAL
        return HardwareType.CPU_ONLY

    def _is_cuda_available(self) -> bool:
        if self._cuda_available: return True
        try:
            import torch
            if torch.cuda.is_available():
                self._cuda_available = True
                return True
        except ImportError: pass
        return False

    def _detect_npu_type(self) -> Optional[HardwareType]:
        if self._npu_type: return self._npu_type
        architecture = self._cpu_info.get("architecture", "").lower()
        if "arm64" in architecture or platform.system() == "Darwin":
            # Heuristic for Apple Silicon
            if platform.system() == "Darwin":
                self._npu_type = HardwareType.NPU_APPLE
                return self._npu_type
        return None

    def refresh_hardware_info(self):
        self._cpu_info = self._get_cpu_info()
        self._gpu_info = self._get_gpu_info()
        self._memory_info = self._get_memory_info()

    def _get_cpu_info(self) -> Dict:
        try:
            return {
                "cores": psutil.cpu_count(logical=False) or 1,
                "threads": psutil.cpu_count(logical=True) or 1,
                "architecture": platform.machine()
            }
        except Exception:
            return {"cores": 1, "threads": 1, "architecture": "unknown"}

    def _get_gpu_info(self) -> Optional[Dict]:
        try:
            import GPUtil
            gpus = GPUtil.getGPUs()
            if gpus:
                gpu = gpus[0]
                return {
                    "name": gpu.name,
                    "memory_gb": round(gpu.memoryTotal / 1024, 2),
                    "vendor": "nvidia",
                    "load": gpu.load * 100
                }
        except ImportError: pass
        except Exception: pass
        return None

    def _get_memory_info(self) -> Dict:
        try:
            mem = psutil.virtual_memory()
            return {
                "total_gb": round(mem.total / (1024**3), 2),
                "available_gb": round(mem.available / (1024**3), 2),
                "percent": mem.percent
            }
        except Exception:
            return {"total_gb": 0, "available_gb": 0, "percent": 0}

    async def get_hardware_state(self) -> HardwareState:
        cpu_usage = psutil.cpu_percent(interval=None)
        gpu_usage = self._gpu_info.get("load", 0.0) if self._gpu_info else 0.0
        memory_available = self._memory_info.get("available_gb", 0.0)
        
        available_tiers = ["cpu", "cloud"]
        if self._gpu_info: available_tiers.append("gpu")
        
        return HardwareState(
            gpu_usage=gpu_usage,
            memory_available_gb=memory_available,
            cpu_usage=cpu_usage,
            available_tiers=available_tiers,
            current_load=cpu_usage / 100.0
        )
