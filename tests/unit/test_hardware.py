import pytest
from backend.core.hardware import HardwareService, HardwareType

def test_hardware_service_initialization():
    service = HardwareService()
    assert service._cpu_info["cores"] >= 1
    assert service._cpu_info["architecture"] != ""

def test_detect_hardware_type():
    service = HardwareService()
    h_type = service.detect_hardware_type()
    assert isinstance(h_type, HardwareType)

@pytest.mark.asyncio
async def test_get_hardware_state():
    service = HardwareService()
    state = await service.get_hardware_state()
    assert state.cpu_usage >= 0.0
    assert state.memory_available_gb >= 0.0
    assert "cpu" in state.available_tiers
