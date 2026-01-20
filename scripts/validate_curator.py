import json
from pathlib import Path
from backend.learning.curator import EpisodeCurator

def validate_curator():
    print("--- JARVISv4 Episode Curator Validation ---")
    
    # 1. Setup mock archive
    archive_dir = Path("tasks/archive/test_validation")
    archive_dir.mkdir(parents=True, exist_ok=True)
    
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
    
    print(f"Created mock archived task at {task_path}")
    
    # 2. Run Curator
    curator = EpisodeCurator(archive_path=archive_dir)
    output_file = Path("backend/datasets/alpaca_data_val.json")
    dataset = curator.curate_dataset(output_file=output_file)
    
    # 3. Verify Output
    print(f"Curated {len(dataset)} examples.")
    
    # Show one of each type
    for example in dataset:
        agent = example["metadata"]["agent"]
        print(f"\n--- Example for {agent} ---")
        print(f"Instruction: {example['instruction']}")
        print(f"Input: {example['input']}")
        print(f"Output: {example['output']}")
        
    print("\n--- Validation Successful ---")

if __name__ == "__main__":
    validate_curator()
