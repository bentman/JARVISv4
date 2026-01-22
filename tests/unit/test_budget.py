import pytest
import os
from pathlib import Path
from backend.core.budget import BudgetService
from backend.core.config.settings import Settings

@pytest.fixture
def temp_settings(tmp_path):
    db_path = tmp_path / "test_budget.db"
    return Settings(
        budget_enforcement_level="block",
        budget_limits={"llm": 10.0, "storage": 5.0},
        budget_db_path=db_path
    )

def test_budget_initialization(temp_settings):
    service = BudgetService(temp_settings)
    assert Path(temp_settings.budget_db_path).exists()
    assert service.enforcement_level == "block"
    assert service.limits["llm"] == 10.0

def test_record_spend(temp_settings):
    service = BudgetService(temp_settings)
    service.record_spend("llm", 1.5, "item1")
    
    status = service.get_status()
    assert status["llm"]["spend"] == 1.5
    assert status["llm"]["remaining"] == 8.5

def test_check_availability_within_limit(temp_settings):
    service = BudgetService(temp_settings)
    assert service.check_availability("llm", 5.0) is True

def test_check_availability_exceeds_limit_block(temp_settings):
    service = BudgetService(temp_settings)
    service.record_spend("llm", 9.0)
    # 9.0 + 2.0 = 11.0 > 10.0 limit
    assert service.check_availability("llm", 2.0) is False

def test_check_availability_exceeds_limit_log(tmp_path):
    db_path = tmp_path / "test_budget_log.db"
    settings = Settings(
        budget_enforcement_level="log",
        budget_limits={"llm": 10.0},
        budget_db_path=db_path
    )
    service = BudgetService(settings)
    service.record_spend("llm", 9.0)
    # Should return True but log (we just check return value)
    assert service.check_availability("llm", 2.0) is True

def test_check_availability_none_level(tmp_path):
    db_path = tmp_path / "test_budget_none.db"
    settings = Settings(
        budget_enforcement_level="none",
        budget_limits={"llm": 1.0},
        budget_db_path=db_path
    )
    service = BudgetService(settings)
    service.record_spend("llm", 2.0)
    assert service.check_availability("llm", 1.0) is True

def test_get_status_multiple_categories(temp_settings):
    service = BudgetService(temp_settings)
    service.record_spend("llm", 1.0)
    service.record_spend("storage", 0.5)
    
    status = service.get_status()
    assert status["llm"]["spend"] == 1.0
    assert status["storage"]["spend"] == 0.5
    assert "llm" in status
    assert "storage" in status

def test_persistence(temp_settings):
    service = BudgetService(temp_settings)
    service.record_spend("llm", 2.5)
    
    # New service instance with same DB
    service2 = BudgetService(temp_settings)
    status = service2.get_status()
    assert status["llm"]["spend"] == 2.5
