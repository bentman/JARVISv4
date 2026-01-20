import json
import pytest
from pathlib import Path
from backend.memory.working_state import WorkingStateManager, REQUIRED_FIELDS
from backend.core.config.settings import Settings

@pytest.fixture
def temp_task_dir(tmp_path):
    d = tmp_path / "tasks"
    d.mkdir()
    return d

@pytest.fixture
def manager(temp_task_dir):
    return WorkingStateManager(temp_task_dir)

def test_create_task(manager, temp_task_dir):
    task_spec = {
        "goal": "Test Task",
        "domain": "testing",
        "constraints": ["Constraint 1"],
        "priority": "high"
    }
    task_id = manager.create_task(task_spec)
    
    assert task_id.startswith("task_")
    task_file = temp_task_dir / f"{task_id}.json"
    assert task_file.exists()
    
    with open(task_file, "r") as f:
        state = json.load(f)
    
    assert state["goal"] == "Test Task"
    assert state["status"] == "CREATED"
    assert state["metadata"]["priority"] == "high"
    for field in REQUIRED_FIELDS:
        assert field in state

def test_load_task(manager):
    task_id = manager.create_task({"goal": "Load Test"})
    state = manager.load_task(task_id)
    assert state["goal"] == "Load Test"

def test_update_task(manager, temp_task_dir):
    task_id = manager.create_task({"goal": "Update Test"})
    
    updates = {"status": "IN_PROGRESS", "domain": "new_domain"}
    manager.update_task(task_id, updates)
    
    state = manager.load_task(task_id)
    assert state["status"] == "IN_PROGRESS"
    assert state["domain"] == "new_domain"

def test_complete_step(manager):
    task_id = manager.create_task({"goal": "Step Test"})
    
    # Set a current step first
    current_step = {
        "index": 1,
        "description": "Step 1",
        "agent": "executor",
        "started_at": "now"
    }
    manager.update_task(task_id, {"current_step": current_step})
    
    manager.complete_step(task_id, 1, "success", artifact="file://test.txt")
    
    state = manager.load_task(task_id)
    assert state["current_step"] is None
    assert len(state["completed_steps"]) == 1
    assert state["completed_steps"][0]["index"] == 1
    assert state["completed_steps"][0]["outcome"] == "success"
    assert state["completed_steps"][0]["artifact"] == "file://test.txt"

def test_archive_task(manager, temp_task_dir):
    task_id = manager.create_task({"goal": "Archive Test"})
    archive_file = manager.archive_task(task_id, reason="finished")
    
    assert not (temp_task_dir / f"{task_id}.json").exists()
    assert archive_file.exists()
    assert "archive" in str(archive_file)
    assert "finished" in archive_file.name

def test_validation_failure(manager):
    task_id = manager.create_task({"goal": "Validation Test"})
    
    # Manually corrupt file to miss a field
    task_file = manager.base_path / f"{task_id}.json"
    with open(task_file, "r") as f:
        state = json.load(f)
    
    del state["goal"]
    with open(task_file, "w") as f:
        json.dump(state, f)
        
    with pytest.raises(ValueError, match="Missing required working state fields: goal"):
        manager.load_task(task_id)

def test_persistence_between_instances(temp_task_dir):
    manager1 = WorkingStateManager(temp_task_dir)
    task_id = manager1.create_task({"goal": "Persistence Test"})
    
    # Modify state
    manager1.update_task(task_id, {"status": "MODIFIED"})
    
    # New manager instance
    manager2 = WorkingStateManager(temp_task_dir)
    state = manager2.load_task(task_id)
    
    assert state["goal"] == "Persistence Test"
    assert state["status"] == "MODIFIED"

def test_config_integration():
    settings = Settings(working_storage_path=Path("custom_tasks"))
    manager = WorkingStateManager(settings.working_storage_path)
    assert manager.base_path == Path("custom_tasks")
    # Clean up
    if manager.base_path.exists():
        import shutil
        shutil.rmtree(manager.base_path)
