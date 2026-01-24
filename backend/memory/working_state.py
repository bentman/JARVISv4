import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

REQUIRED_FIELDS = [
    "task_id",
    "goal",
    "status",
    "domain",
    "constraints",
    "current_step",
    "completed_steps",
    "next_steps",
    "metadata"
]

class WorkingStateManager:
    """Manages ephemeral task state on filesystem using JSON."""
    
    def __init__(self, base_path: Path):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.archive_path = self.base_path / "archive"

    def list_active_task_ids(self) -> List[str]:
        """List task IDs for non-archived task files."""
        task_ids: List[str] = []
        for task_file in self.base_path.glob("task_*.json"):
            task_ids.append(task_file.stem)
        return sorted(task_ids)

    def list_incomplete_task_ids(self) -> List[str]:
        """List task IDs that are not completed or failed."""
        incomplete: List[str] = []
        for task_id in self.list_active_task_ids():
            try:
                state = self.load_task(task_id)
            except Exception as exc:
                logger.warning(f"Skipping task {task_id}: {exc}")
                continue
            status = state.get("status")
            if status not in {"COMPLETED", "FAILED"}:
                incomplete.append(task_id)
        return incomplete
    
    def _validate_state(self, state: Dict[str, Any]) -> None:
        """Ensure the state contains all required ECF Tier 1 fields."""
        missing = [field for field in REQUIRED_FIELDS if field not in state]
        if missing:
            raise ValueError(f"Missing required working state fields: {', '.join(missing)}")

    def _generate_task_id(self) -> str:
        """Generate a unique task ID."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        return f"task_{timestamp}_{unique_id}"

    def create_task(self, task_spec: Dict[str, Any]) -> str:
        """Initialize new task state."""
        task_id = self._generate_task_id()
        task_file = self.base_path / f"{task_id}.json"
        
        state = {
            "task_id": task_id,
            "goal": task_spec.get("goal", "No goal specified"),
            "status": "CREATED",
            "domain": task_spec.get("domain", "general"),
            "constraints": task_spec.get("constraints", []),
            "current_step": None,
            "completed_steps": [],
            "next_steps": task_spec.get("next_steps", []),
            "metadata": {
                "created_at": datetime.now().isoformat(),
                "priority": task_spec.get("priority", "normal")
            }
        }
        
        self._validate_state(state)
        
        with open(task_file, "w") as f:
            json.dump(state, f, indent=2)
        
        logger.info(f"Created task {task_id} at {task_file}")
        return task_id

    def load_task(self, task_id: str) -> Dict[str, Any]:
        """Load task state from disk."""
        task_file = self.base_path / f"{task_id}.json"
        if not task_file.exists():
            raise FileNotFoundError(f"Task file not found: {task_file}")
            
        with open(task_file, "r") as f:
            state = json.load(f)
            
        self._validate_state(state)
        return state

    def update_task(self, task_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update task state (atomic operation)."""
        state = self.load_task(task_id)
        state.update(updates)
        
        self._validate_state(state)
        
        task_file = self.base_path / f"{task_id}.json"
        temp_file = task_file.with_suffix(".tmp")
        
        try:
            # Atomic write
            with open(temp_file, "w") as f:
                json.dump(state, f, indent=2)
            temp_file.replace(task_file)
        except Exception as e:
            if temp_file.exists():
                temp_file.unlink()
            raise e
            
        return state

    def complete_step(
        self, 
        task_id: str, 
        step_index: int, 
        outcome: str, 
        artifact: Optional[str] = None,
        tool_name: Optional[str] = None,
        tool_params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Mark current step as completed."""
        state = self.load_task(task_id)
        
        if not state.get("current_step"):
            raise ValueError(f"No active step to complete for task {task_id}")
            
        if state["current_step"].get("index") != step_index:
            logger.warning(f"Completing step {step_index} but current_step index is {state['current_step'].get('index')}")

        completed_step = {
            "index": step_index,
            "description": state["current_step"].get("description"),
            "outcome": outcome,
            "artifact": artifact,
            "tool_name": tool_name,
            "tool_params": tool_params,
            "completed_at": datetime.now().isoformat()
        }
        
        state["completed_steps"].append(completed_step)
        state["current_step"] = None
        state["status"] = "IN_PROGRESS"
        
        return self.update_task(task_id, state)

    def archive_task(self, task_id: str, reason: str = "completed") -> Path:
        """Move completed task to archive."""
        task_file = self.base_path / f"{task_id}.json"
        if not task_file.exists():
            raise FileNotFoundError(f"Task file not found: {task_file}")
            
        archive_dir = self.archive_path / datetime.now().strftime("%Y-%m")
        archive_dir.mkdir(parents=True, exist_ok=True)
        
        archive_file = archive_dir / f"{task_id}_{reason}.json"
        task_file.rename(archive_file)
        
        logger.info(f"Archived task {task_id} to {archive_file}")
        return archive_file
