import asyncio
import json
import pytest
import respx
import yaml
from httpx import Response
from pathlib import Path
from backend.core.controller import ECFController
from backend.tools.base import BaseTool, ToolDefinition
from backend.learning.curator import EpisodeCurator
from backend.learning.mixer import DatasetMixer
from backend.learning.train import LearnerOrchestrator

class IntegrationTemplateTool(BaseTool):
    @property
    def definition(self):
        return ToolDefinition(
            name="integration_template_tool",
            description="A standardized tool for integration testing",
            parameters={
                "type": "object",
                "properties": {
                    "data": {"type": "string"}
                },
                "required": ["data"]
            }
        )
    async def execute(self, **kwargs):
        return {"processed_data": kwargs.get("data"), "status": "INTEGRATION_SUCCESS"}

@pytest.mark.asyncio
async def test_full_learning_cycle(tmp_path, monkeypatch):
    """
    Validates the full ECF Learning Cycle:
    Task Execution -> Episode Curation -> Dataset Mixing -> Training Orchestration (Dry Run).
    """
    # Setup isolated environment paths
    storage_root = tmp_path / "tasks"
    archive_dir = storage_root / "archive"
    monkeypatch.setenv("WORKING_STORAGE_PATH", str(storage_root))
    
    # 1. GENERATE EPISODE
    # We execute a task via the ECFController to create a successful execution trace.
    controller = ECFController()
    controller.registry.register_tool(IntegrationTemplateTool())
    
    goal = "Execute a full cycle integration test"
    
    # Mock LLM responses for Planner and Executor
    planner_plan = {
        "tasks": [
            {"id": "1", "description": "Run the integration template tool", "dependencies": [], "estimated_duration": "1m"}
        ]
    }
    executor_selection = {
        "tool": "integration_template_tool",
        "params": {"data": "Learning Cycle Check"},
        "rationale": "Matches the goal for training data generation"
    }
    
    async with respx.mock(base_url="http://mock-llm/v1") as respx_mock:
        controller.llm.client.base_url = "http://mock-llm/v1"
        
        respx_mock.post("http://mock-llm/v1/chat/completions").mock(side_effect=[
            Response(200, json={"choices": [{"message": {"content": json.dumps(planner_plan)}}]}),
            Response(200, json={"choices": [{"message": {"content": json.dumps(executor_selection)}}]})
        ])
        
        task_id = await controller.run_task(goal)
        
        assert task_id.startswith("task_")
        assert controller.state.value == "COMPLETED"
        
        # Verify archive exists
        archive_files = list(archive_dir.rglob(f"*{task_id}*"))
        assert len(archive_files) == 1
    
    # 2. CURATE
    # Extract training examples from the archived episode.
    curator = EpisodeCurator(archive_path=archive_dir)
    curriculum_file = tmp_path / "curriculum.json"
    dataset = curator.curate_dataset(output_file=curriculum_file)
    
    assert len(dataset) >= 2  # At least 1 Planner + 1 Executor example
    assert curriculum_file.exists()
    
    agents_represented = {item["metadata"]["agent"] for item in dataset}
    assert "planner" in agents_represented
    assert "executor" in agents_represented

    # 3. MIX
    # Blend the newly curated data with the basal anchor set.
    basal_path = Path("data/training/basal_set.json")
    # Create a dummy basal set if it doesn't exist for some reason, though it should be in repo
    if not basal_path.exists():
         basal_path.parent.mkdir(parents=True, exist_ok=True)
         with open(basal_path, "w") as f:
             json.dump([{"instruction": "Basal", "input": "", "output": ""}] * 5, f)

    mixer = DatasetMixer(basal_path=basal_path)
    mixed_file = tmp_path / "mixed_payload.json"
    # Use a lower curriculum ratio (0.2) to force inclusion of basal data given only 2 curriculum items
    mixed_data = mixer.mix_datasets(
        curriculum_path=curriculum_file, 
        output_path=mixed_file,
        curriculum_ratio=0.2
    )
    
    assert len(mixed_data) > len(dataset)
    assert mixed_file.exists()

    # 4. TRAIN (DRY RUN)
    # Verify the training orchestrator can consume the mixed dataset and initialize correctly.
    test_config = {
        "lora": {
            "r": 16,
            "alpha": 32,
            "dropout": 0.05,
            "bias": "none"
        },
        "training": {
            "learning_rate": 2.0e-4,
            "optim": "adamw_8bit"
        },
        "paths": {
            "basal": str(basal_path),
            "curriculum": str(curriculum_file),
            "output_dir": str(tmp_path / "model_candidate")
        }
    }
    config_path = tmp_path / "test_config.yaml"
    with open(config_path, "w") as f:
        yaml.dump(test_config, f)
        
    orchestrator = LearnerOrchestrator(config_path=config_path)
    success = orchestrator.run_training_cycle(dry_run=True)
    
    assert success is True
