import pytest
from pathlib import Path
from backend.learning.train import LearnerOrchestrator

def test_learner_orchestrator_dry_run(tmp_path):
    # 1. Setup mock config and data
    config_path = tmp_path / "config.yaml"
    basal_path = tmp_path / "basal.json"
    curriculum_path = tmp_path / "curriculum.json"
    output_dir = tmp_path / "models"
    output_dir.mkdir()
    
    import json
    with open(basal_path, "w") as f:
        json.dump([{"instruction": "B1"}], f)
    with open(curriculum_path, "w") as f:
        json.dump([{"instruction": "C1"}], f)
        
    config_content = f"""
lora:
  r: 16
  alpha: 32
  dropout: 0.05
  bias: "none"
training:
  learning_rate: 2.0e-4
  optim: "adamw_8bit"
  max_steps: 500
  batch_size: 4
  gradient_accumulation_steps: 4
paths:
  basal: "{basal_path.as_posix()}"
  curriculum: "{curriculum_path.as_posix()}"
  output_dir: "{output_dir.as_posix()}"
"""
    with open(config_path, "w") as f:
        f.write(config_content)
        
    # 2. Run Orchestrator
    orchestrator = LearnerOrchestrator(config_path=config_path)
    success = orchestrator.run_training_cycle(dry_run=True)
    
    assert success is True
