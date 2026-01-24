import logging
import asyncio
from enum import Enum
from typing import Any, Dict, List, Optional
from pathlib import Path

from backend.core.config.settings import Settings, load_settings
from backend.core.llm.provider import OpenAIProvider
from backend.memory.working_state import WorkingStateManager
from backend.agents.planner.planner import PlannerAgent, InvalidPlanError
from backend.agents.executor.executor import ExecutorAgent
from backend.tools.registry.registry import ToolRegistry
from backend.tools.web_search import WebSearchTool

logger = logging.getLogger(__name__)

class ControllerState(Enum):
    INITIALIZING = "INITIALIZING"
    PLANNING = "PLANNING"
    EXECUTING = "EXECUTING"
    VERIFYING = "VERIFYING"
    ARCHIVING = "ARCHIVING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class ECFController:
    """
    Authoritative spine of the system managing the ECF Layer 1 loop.
    Coordinates between State, Planner, and Executor.
    """
    
    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or load_settings()
        self.state = ControllerState.INITIALIZING
        
        # Initialize Infrastructure
        self.registry = ToolRegistry()
        self.llm = OpenAIProvider(
            model=self.settings.llm_model,
            api_key=self.settings.llm_api_key,
            base_url=self.settings.llm_base_url
        )
        self.state_manager = WorkingStateManager(
            base_path=self.settings.working_storage_path
        )
        
        # Initialize Agents
        self.planner = PlannerAgent(self.llm, self.state_manager)
        self.executor = ExecutorAgent(self.llm, self.registry)
        
        # Register Default Tools
        self.registry.register_tool(WebSearchTool(self.settings))
        
        logger.info("ECFController initialized and READY.")

    async def run_task(self, goal: str) -> str:
        """
        Executes a task to completion using the ECF loop.
        
        Returns:
            task_id: The ID of the processed task.
        """
        task_id: Optional[str] = None
        
        try:
            # PHASE 1: PLANNING
            self.state = ControllerState.PLANNING
            logger.info(f"Transitioning to {self.state.value} for goal: {goal}")
            
            try:
                task_id = await self.planner.generate_plan(goal)
            except InvalidPlanError as e:
                logger.error(f"Planning failed: {str(e)}")
                self.state = ControllerState.FAILED
                task_id = self.state_manager.create_task({
                    "goal": goal,
                    "domain": "general",
                    "constraints": []
                })
                self.state_manager.update_task(task_id, {"status": "FAILED"})
                self.state_manager.archive_task(task_id, reason="failed_plan")
                return "FAILED_PLAN" # Or handle better if we had a task_id already
            
            # PHASE 2: EXECUTING
            self.state = ControllerState.EXECUTING
            logger.info(f"Transitioning to {self.state.value} for task_id: {task_id}")
            
            while True:
                # Load current state
                task_state = self.state_manager.load_task(task_id)
                
                # Check if we have steps remaining
                next_steps = task_state.get("next_steps", [])
                if not next_steps:
                    logger.info("No more steps in plan. Completion reached.")
                    break
                
                # Pop the next step
                current_step = next_steps[0]
                step_index = len(task_state.get("completed_steps", []))
                
                # Update state to reflect current active step
                self.state_manager.update_task(task_id, {
                    "current_step": {
                        "index": step_index,
                        "description": current_step["description"]
                    },
                    "next_steps": next_steps[1:] # Remove from next
                })
                
                logger.info(f"Executing Step {step_index}: {current_step['description']}")
                
                # Execute
                outcome = await self.executor.execute_step(
                    current_step["description"],
                    context={"task_id": task_id, "goal": goal}
                )
                
                if outcome["status"] == "FAILED":
                    logger.error(f"Step {step_index} failed: {outcome.get('error')}")
                    self.state_manager.update_task(task_id, {"status": "FAILED"})
                    self.state_manager.archive_task(task_id, reason="failed_execute")
                    self.state = ControllerState.FAILED
                    break
                
                # Record success
                self.state_manager.complete_step(
                    task_id,
                    step_index=step_index,
                    outcome="SUCCESS",
                    artifact=str(outcome.get("result")),
                    tool_name=outcome.get("tool"),
                    tool_params=outcome.get("params")
                )
            
            # PHASE 3: ARCHIVING
            if self.state != ControllerState.FAILED:
                self.state = ControllerState.ARCHIVING
                logger.info(f"Transitioning to {self.state.value}")
                self.state_manager.update_task(task_id, {"status": "COMPLETED"})
                self.state_manager.archive_task(task_id)
                self.state = ControllerState.COMPLETED
                logger.info(f"Task {task_id} COMPLETED and ARCHIVED.")
            else:
                logger.error(f"Task {task_id} halted in FAILED state.")
                
            return task_id or "UNKNOWN"
            
        except Exception as e:
            logger.exception(f"Unexpected controller error: {str(e)}")
            self.state = ControllerState.FAILED
            if task_id:
                self.state_manager.update_task(task_id, {"status": "FAILED"})
                self.state_manager.archive_task(task_id, reason="error")
            return task_id or "ERROR"
        finally:
            await self.llm.close()
