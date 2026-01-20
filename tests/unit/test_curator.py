import json
import pytest
from pathlib import Path
from backend.learning.curator import EpisodeCurator

@pytest.fixture
def mock_archive(tmp_path):
    archive_dir = tmp_path / "archive"
    archive_dir.mkdir()
    
    mock_task = {
        "task_id": "task_val_123",
        "goal": "Test tool metadata persistence",
        "status": "COMPLETED",
        "domain": "testing",
        "constraints": ["constraint_1"],
        "completed_steps": [
            {
                "index": 0,
                "description": "Calculate square root",
                "outcome": "SUCCESS",
                "artifact": "4.0",
                "tool_name": "math_tool",
                "tool_params": {"action": "sqrt", "value": 16},
                "completed_at": "2026-01-19T19:30:00"
            }
        ],
        "next_steps": [],
        "metadata": {"created_at": "2026-01-19T19:00:00"}
    }
    
    task_path = archive_dir / "task_val_123_completed.json"
    with open(task_path, "w") as f:
        json.dump(mock_task, f, indent=2)
        
    return archive_dir

def test_curate_dataset_extraction(mock_archive, tmp_path):
    curator = EpisodeCurator(archive_path=mock_archive)
    output_file = tmp_path / "alpaca_data.json"
    
    dataset = curator.curate_dataset(output_file=output_file)
    
    assert len(dataset) == 2
    
    planner_example = next(ex for ex in dataset if ex["metadata"]["agent"] == "planner")
    executor_example = next(ex for ex in dataset if ex["metadata"]["agent"] == "executor")
    
    assert planner_example["instruction"] == "Decompose this goal into a concrete plan."
    assert "Test tool metadata persistence" in planner_example["input"]
    
    assert executor_example["instruction"] == "Execute this task step: Calculate square root"
    assert "math_tool" in executor_example["output"]
    assert "16" in executor_example["output"]

def test_validate_admission_failure(tmp_path):
    archive_dir = tmp_path / "archive_fail"
    archive_dir.mkdir()
    
    incomplete_task = {
        "task_id": "task_fail",
        "status": "FAILED",
        "completed_steps": [{"outcome": "FAILED"}]
    }
    
    with open(archive_dir / "fail.json", "w") as f:
        json.dump(incomplete_task, f)
        
    curator = EpisodeCurator(archive_path=archive_dir)
    dataset = curator.curate_dataset()
    
    assert len(dataset) == 0
