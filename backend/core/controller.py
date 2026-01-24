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
from backend.memory.stores.trace_store import TraceStore

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
        self.last_error: Optional[str] = None
        
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
        trace_db_path = Path(self.settings.working_storage_path) / "traces.db"
        self.trace_store = TraceStore(str(trace_db_path))
        
        # Initialize Agents
        self.planner = PlannerAgent(self.llm, self.state_manager)
        self.executor = ExecutorAgent(self.llm, self.registry)
        
        # Register Default Tools
        self.registry.register_tool(WebSearchTool(self.settings))
        
        logger.info("ECFController initialized and READY.")

    async def _execute_remaining_steps(self, task_id: str, goal: str, max_steps: Optional[int] = None) -> int:
        """Execute remaining steps for an existing task state."""
        executed_steps = 0
        while True:
            task_state = self.state_manager.load_task(task_id)
            next_steps = task_state.get("next_steps", [])
            if not next_steps:
                logger.info("No more steps in plan. Completion reached.")
                break

            if max_steps is not None and executed_steps >= max_steps:
                logger.info("Max steps reached; halting execution loop.")
                break

            current_step = next_steps[0]
            step_index = len(task_state.get("completed_steps", []))

            self.state_manager.update_task(task_id, {
                "current_step": {
                    "index": step_index,
                    "description": current_step["description"]
                },
                "next_steps": next_steps[1:]
            })

            logger.info(f"Executing Step {step_index}: {current_step['description']}")
            self.trace_store.append_decision(
                task_id,
                "step_started",
                {"step_index": step_index, "description": current_step["description"]}
            )

            outcome = await self.executor.execute_step(
                current_step["description"],
                context={"task_id": task_id, "goal": goal}
            )
            self.trace_store.append_tool_call(
                task_id=task_id,
                step_index=step_index,
                tool_name=outcome.get("tool"),
                params=outcome.get("params", {}),
                status=outcome.get("status", "FAILED"),
                result=str(outcome.get("result")) if outcome.get("result") is not None else None,
                error=outcome.get("error")
            )
            self.trace_store.append_validation(
                task_id,
                "step_execution",
                "PASS" if outcome.get("status") == "SUCCESS" else "FAIL",
                {
                    "step_index": step_index,
                    "tool": outcome.get("tool"),
                    "error": outcome.get("error")
                }
            )

            if outcome["status"] == "FAILED":
                logger.error(f"Step {step_index} failed: {outcome.get('error')}")
                self.last_error = outcome.get("error") or "Step execution failed"
                self.state_manager.update_task(task_id, {"status": "FAILED"})
                self.state_manager.archive_task(task_id, reason="failed_execute")
                self.state = ControllerState.FAILED
                break

            self.state_manager.complete_step(
                task_id,
                step_index=step_index,
                outcome="SUCCESS",
                artifact=str(outcome.get("result")),
                tool_name=outcome.get("tool"),
                tool_params=outcome.get("params")
            )
            executed_steps += 1

        return executed_steps

    async def resume_task(self, task_id: str, max_steps: Optional[int] = None) -> str:
        """Resume execution of an existing task using on-disk state."""
        self.last_error = None
        task_state = self.state_manager.load_task(task_id)
        status = task_state.get("status")
        if status in {"COMPLETED", "FAILED"}:
            raise ValueError(f"Task {task_id} is not resumable (status={status})")

        if task_state.get("current_step"):
            raise ValueError(f"Cannot resume task {task_id} with current_step in-flight")

        goal = task_state.get("goal", "")
        self.state = ControllerState.EXECUTING
        logger.info(f"Resuming task {task_id} with status {status}")

        await self._execute_remaining_steps(task_id, goal, max_steps=max_steps)

        if self.state != ControllerState.FAILED:
            task_state = self.state_manager.load_task(task_id)
            if not task_state.get("next_steps"):
                self.state = ControllerState.ARCHIVING
                logger.info(f"Transitioning to {self.state.value}")
                self.state_manager.update_task(task_id, {"status": "COMPLETED"})
                self.state_manager.archive_task(task_id)
                self.state = ControllerState.COMPLETED
                logger.info(f"Task {task_id} COMPLETED and ARCHIVED.")
        else:
            logger.error(f"Task {task_id} halted in FAILED state.")

        return task_id

    async def run_task(self, goal: str) -> str:
        """
        Executes a task to completion using the ECF loop.
        
        Returns:
            task_id: The ID of the processed task.
        """
        task_id: Optional[str] = None
        self.last_error = None
        
        try:
            # PHASE 1: PLANNING
            self.state = ControllerState.PLANNING
            logger.info(f"Transitioning to {self.state.value} for goal: {goal}")

            if task_id is None:
                task_id = self.state_manager.create_task({
                    "goal": goal,
                    "domain": "general",
                    "constraints": [],
                    "next_steps": []
                })
            
            try:
                plan_task_id = await self.planner.generate_plan(goal)
                if plan_task_id != task_id:
                    logger.warning("Planner task_id differed from pre-created task; using planner task_id")
                    task_id = plan_task_id
                self.trace_store.append_decision(
                    task_id,
                    "plan_accepted",
                    {"goal": goal}
                )
                self.trace_store.append_validation(
                    task_id,
                    "plan_valid",
                    "PASS",
                    {"goal": goal}
                )
            except InvalidPlanError as e:
                logger.error(f"Planning failed: {str(e)}")
                self.state = ControllerState.FAILED
                self.last_error = str(e)
                self.trace_store.append_decision(
                    task_id,
                    "plan_rejected",
                    {"error": str(e), "goal": goal}
                )
                self.trace_store.append_validation(
                    task_id,
                    "plan_valid",
                    "FAIL",
                    {"error": str(e), "goal": goal}
                )
                self.state_manager.update_task(task_id, {"status": "FAILED"})
                self.state_manager.archive_task(task_id, reason="failed_plan")
                return task_id
            
            # PHASE 2: EXECUTING
            self.state = ControllerState.EXECUTING
            logger.info(f"Transitioning to {self.state.value} for task_id: {task_id}")
            
            await self._execute_remaining_steps(task_id, goal)
            
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
            self.last_error = f"{type(e).__name__}: {e}"
            if task_id is None:
                task_id = self.state_manager.create_task({
                    "goal": goal,
                    "domain": "general",
                    "constraints": [],
                    "next_steps": []
                })
            self.trace_store.append_decision(
                task_id,
                "controller_error",
                {"error": str(e)}
            )
            self.state_manager.update_task(task_id, {"status": "FAILED"})
            self.state_manager.archive_task(task_id, reason="error")
            return task_id
        finally:
            await self.llm.close()
