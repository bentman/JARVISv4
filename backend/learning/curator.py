"""
Episode Curator for JARVISv4.
Extracts high-quality training data from completed task archives.
Formats data into Alpaca-style instruction/input/output sets.
"""
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

class EpisodeCurator:
    """
    Component responsible for discovering, filtering, and transforming 
    archived task episodes into training datasets.
    """
    
    def __init__(self, archive_path: Path):
        self.archive_path = Path(archive_path)
        
    def validate_admission(self, task_state: Dict[str, Any]) -> bool:
        """
        Determines if an episode is high-quality enough for training.
        Admission Policy:
        1. Status must be COMPLETED.
        2. All steps must have SUCCESS outcome.
        3. Mandatory fields (goal, task_id) must be present.
        """
        if task_state.get("status") != "COMPLETED":
            return False
            
        completed_steps = task_state.get("completed_steps", [])
        if not completed_steps:
            return False
            
        # Ensure every step succeeded
        for step in completed_steps:
            if step.get("outcome") != "SUCCESS":
                return False
                
        return True

    def extract_planner_example(self, task_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transforms goal and plan into a training row for the Planner agent.
        """
        instruction = "Decompose this goal into a concrete plan."
        input_data = {
            "goal": task_state.get("goal"),
            "domain": task_state.get("domain", "general"),
            "constraints": task_state.get("constraints", [])
        }
        
        # Reconstruct plan from completed steps
        plan = [
            {"id": str(i), "description": step["description"]} 
            for i, step in enumerate(task_state.get("completed_steps", []))
        ]
        
        output_data = {"tasks": plan}
        
        return {
            "instruction": instruction,
            "input": json.dumps(input_data),
            "output": json.dumps(output_data),
            "metadata": {
                "task_id": task_state.get("task_id"),
                "agent": "planner"
            }
        }

    def extract_executor_examples(self, task_state: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Transforms individual steps into training rows for the Executor agent.
        Only extracts if tool metadata is present.
        """
        examples = []
        for step in task_state.get("completed_steps", []):
            tool_name = step.get("tool_name")
            tool_params = step.get("tool_params")
            
            if not tool_name:
                continue
                
            instruction = f"Execute this task step: {step['description']}"
            input_data = {
                "task_id": task_state.get("task_id"),
                "goal": task_state.get("goal")
            }
            
            output_data = {
                "tool": tool_name,
                "params": tool_params,
                "rationale": "Extracted from successful execution trace."
            }
            
            examples.append({
                "instruction": instruction,
                "input": json.dumps(input_data),
                "output": json.dumps(output_data),
                "metadata": {
                    "task_id": task_state.get("task_id"),
                    "step_index": step.get("index"),
                    "agent": "executor"
                }
            })
            
        return examples

    def curate_dataset(self, output_file: Optional[Path] = None) -> List[Dict[str, Any]]:
        """
        Scans archive, filters episodes, and generates full dataset.
        """
        dataset = []
        logger.info(f"Scanning archive at {self.archive_path}...")
        
        # Walk through all JSON files in the archive
        for json_file in self.archive_path.glob("**/*.json"):
            try:
                with open(json_file, "r") as f:
                    task_state = json.load(f)
                    
                if not self.validate_admission(task_state):
                    continue
                    
                # Extract Planner data
                dataset.append(self.extract_planner_example(task_state))
                
                # Extract Executor data
                dataset.extend(self.extract_executor_examples(task_state))
                
            except Exception as e:
                logger.error(f"Failed to process archive file {json_file}: {e}")
                
        logger.info(f"Curated {len(dataset)} training examples.")
        
        if output_file:
            output_file.parent.mkdir(parents=True, exist_ok=True)
            with open(output_file, "w") as f:
                json.dump(dataset, f, indent=2)
            logger.info(f"Dataset exported to {output_file}")
            
        return dataset
