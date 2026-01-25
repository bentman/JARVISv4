import logging
import asyncio
import json
import time
from enum import Enum
from typing import Any, Dict, List, Optional
from pathlib import Path

from backend.core.config.settings import Settings, load_settings
from backend.core.llm.provider import OpenAIProvider
from backend.memory.working_state import WorkingStateManager
from backend.agents.planner.planner import PlannerAgent, InvalidPlanError
from backend.agents.executor.executor import ExecutorAgent, EXECUTOR_SYSTEM_PROMPT
from backend.tools.registry.registry import ToolRegistry
from backend.tools.web_search import WebSearchTool
from backend.tools.text_output import TextOutputTool
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
    MAX_PLANNED_STEPS = 100
    MAX_EXECUTED_STEPS = 100
    
    def __init__(
        self,
        settings: Optional[Settings] = None,
        llm_timeout_seconds: Optional[float] = None,
        llm_max_retries: Optional[int] = None
    ):
        self.settings = settings or load_settings()
        self.state = ControllerState.INITIALIZING
        self.last_error: Optional[str] = None
        
        # Initialize Infrastructure
        self.registry = ToolRegistry()
        provider_kwargs: Dict[str, Any] = {
            "model": self.settings.llm_model,
            "api_key": self.settings.llm_api_key,
            "base_url": self.settings.llm_base_url
        }
        if llm_timeout_seconds is not None:
            provider_kwargs["timeout"] = llm_timeout_seconds
        if llm_max_retries is not None:
            provider_kwargs["max_retries"] = llm_max_retries
        self.llm = OpenAIProvider(**provider_kwargs)
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
        self.registry.register_tool(TextOutputTool())
        
        logger.info("ECFController initialized and READY.")

    def list_task_summaries(self) -> List[Dict[str, Any]]:
        """Read-only enumeration of task summaries from disk."""
        summaries: List[Dict[str, Any]] = []

        active_ids = self.state_manager.list_active_task_ids()
        for task_id in active_ids:
            try:
                state = self.state_manager.load_task(task_id)
            except Exception as exc:
                logger.warning(f"Skipping task {task_id}: {exc}")
                continue
            summaries.append({
                "task_id": task_id,
                "lifecycle": "ACTIVE",
                "status": state.get("status"),
                "completed_steps": len(state.get("completed_steps", [])),
                "next_steps": len(state.get("next_steps", [])),
                "has_current_step": bool(state.get("current_step")),
                "source_path": str(self.settings.working_storage_path / f"{task_id}.json")
            })

        for archived_path in self.state_manager.list_archived_task_paths():
            try:
                state = json.loads(archived_path.read_text())
            except Exception as exc:
                logger.warning(f"Skipping archived task {archived_path}: {exc}")
                continue
            task_id = state.get("task_id", archived_path.stem)
            summaries.append({
                "task_id": task_id,
                "lifecycle": "ARCHIVED",
                "status": state.get("status"),
                "completed_steps": len(state.get("completed_steps", [])),
                "next_steps": len(state.get("next_steps", [])),
                "has_current_step": bool(state.get("current_step")),
                "source_path": str(archived_path)
            })

        def _sort_key(item: Dict[str, Any]) -> tuple:
            lifecycle_rank = 0 if item.get("lifecycle") == "ACTIVE" else 1
            return (lifecycle_rank, item.get("task_id", ""))

        return sorted(summaries, key=_sort_key)

    def summarize_task_outcomes(self) -> Dict[str, Any]:
        """Read-only analytics derived from on-disk ACTIVE + ARCHIVED task artifacts."""
        totals: Dict[str, int] = {}
        failed_by_cause: Dict[str, int] = {}
        total_count = 0

        summaries = self.list_task_summaries()
        for summary in summaries:
            source_path = summary.get("source_path")
            if not source_path:
                continue
            try:
                state = json.loads(Path(source_path).read_text())
            except Exception as exc:
                logger.warning(f"Skipping task analytics for {source_path}: {exc}")
                continue

            total_count += 1
            status = state.get("status") or "unknown"
            totals[status] = totals.get(status, 0) + 1

            if status == "FAILED":
                failure_cause = state.get("failure_cause") or "unknown"
                failed_by_cause[failure_cause] = failed_by_cause.get(failure_cause, 0) + 1

        return {
            "total": total_count,
            "by_status": totals,
            "failed_by_cause": failed_by_cause
        }

    async def orchestrate_task_batch(
        self,
        goals: List[str],
        max_tasks: int = 3,
        min_stall_age_seconds: float = 0
    ) -> Dict[str, Any]:
        """Run a bounded batch of tasks sequentially and stop on first analytics failure."""
        task_ids: List[str] = []
        decisions: List[Dict[str, Any]] = []
        stop_reason = "no_goals"

        settings = self.settings
        for goal in goals[:max_tasks]:
            controller = ECFController(settings=settings)
            task_id = await controller.run_task(goal)
            task_ids.append(task_id)

            await controller.supervisor_resume_stalled_tasks(
                min_age_seconds=min_stall_age_seconds,
                max_tasks=1
            )
            analytics = controller.summarize_task_outcomes()
            failed_total = sum(analytics.get("failed_by_cause", {}).values())

            action = "continue"
            if failed_total > 0:
                action = "stop"
                stop_reason = "failure_detected"
            decisions.append({
                "task_id": task_id,
                "analytics": analytics,
                "action": action
            })

            if action == "stop":
                break

        if task_ids and stop_reason == "no_goals":
            if len(task_ids) >= min(max_tasks, len(goals)):
                stop_reason = "max_tasks_reached"

        return {
            "task_ids": task_ids,
            "decisions": decisions,
            "stop_reason": stop_reason
        }

    async def supervisor_resume_stalled_tasks(
        self,
        min_age_seconds: float,
        max_tasks: int = 10
    ) -> List[str]:
        """Resume eligible ACTIVE tasks older than min_age_seconds (deterministic order)."""
        resumed: List[str] = []

        summaries = self.list_task_summaries()
        for summary in summaries:
            if len(resumed) >= max_tasks:
                break
            if summary.get("lifecycle") != "ACTIVE":
                continue
            status = summary.get("status")
            if status != "IN_PROGRESS":
                continue
            if summary.get("has_current_step"):
                continue

            source_path = summary.get("source_path")
            if not source_path:
                continue

            try:
                mtime = Path(source_path).stat().st_mtime
            except FileNotFoundError:
                continue

            age_seconds = time.time() - mtime
            if age_seconds < min_age_seconds:
                continue

            task_id = summary.get("task_id")
            if not task_id:
                continue

            await self.resume_task(task_id)
            resumed.append(task_id)

        return resumed

    async def _execute_remaining_steps(self, task_id: str, goal: str, max_steps: Optional[int] = None) -> int:
        """Execute remaining steps for an existing task state."""
        executed_steps = 0
        while True:
            task_state = self.state_manager.load_task(task_id)
            next_steps = task_state.get("next_steps", [])
            if not next_steps:
                logger.info("No more steps in plan. Completion reached.")
                break

            if executed_steps >= self.MAX_EXECUTED_STEPS:
                self.last_error = (
                    f"Exceeded MAX_EXECUTED_STEPS={self.MAX_EXECUTED_STEPS}"
                )
                self.state_manager.update_task(task_id, {
                    "status": "FAILED",
                    "error": self.last_error,
                    "failure_cause": "execution_step_failed"
                })
                self.state_manager.archive_task(task_id, reason="failed_execute")
                self.state = ControllerState.FAILED
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
                self.state_manager.update_task(task_id, {
                    "status": "FAILED",
                    "error": self.last_error,
                    "failure_cause": "execution_step_failed"
                })
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

    async def _select_tool_for_step(self, step_description: str, goal: str, task_id: str) -> Dict[str, Any]:
        tool_defs = self.registry.get_tool_definitions()
        prompt = EXECUTOR_SYSTEM_PROMPT.format(
            tool_definitions=json.dumps(tool_defs, indent=2)
        )
        user_prompt = (
            f"Task Step: {step_description}\n"
            f"Context: {json.dumps({'task_id': task_id, 'goal': goal})}"
        )
        full_prompt = f"{prompt}\n\n{user_prompt}"
        response = await self.llm.generate(full_prompt)
        return self.executor._parse_response(response)

    async def resume_task(self, task_id: str, max_steps: Optional[int] = None) -> str:
        """Resume execution of an existing task using on-disk state."""
        self.last_error = None
        task_state = self.state_manager.load_task(task_id)
        status = task_state.get("status")
        if status in {"COMPLETED", "FAILED"}:
            raise ValueError(f"Task {task_id} is not resumable (status={status})")

        current_step = task_state.get("current_step")
        if current_step:
            step_description = current_step.get("description")
            if step_description:
                next_steps = task_state.get("next_steps", [])
                if not next_steps or next_steps[0].get("description") != step_description:
                    next_steps = [
                        {"description": step_description}
                    ] + next_steps
                task_state = self.state_manager.update_task(task_id, {
                    "current_step": None,
                    "next_steps": next_steps,
                    "status": "IN_PROGRESS"
                })
                logger.info(
                    "Re-queued in-flight step for deterministic resume: "
                    f"task_id={task_id} description={step_description}"
                )
            else:
                raise ValueError(f"Cannot resume task {task_id} with incomplete current_step")

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
                await self.planner.generate_plan(
                    goal,
                    constraints=[],
                    domain="general",
                    task_id=task_id
                )
                task_state = self.state_manager.load_task(task_id)
                planned_steps = task_state.get("next_steps", [])
                if len(planned_steps) > self.MAX_PLANNED_STEPS:
                    raise InvalidPlanError(
                        "Plan has too many steps: "
                        f"{len(planned_steps)} > MAX_PLANNED_STEPS={self.MAX_PLANNED_STEPS}"
                    )
                for index, step in enumerate(planned_steps):
                    step_description = step.get("description") if isinstance(step, dict) else None
                    if not step_description:
                        raise InvalidPlanError("Plan step missing description")
                    selection = await self._select_tool_for_step(step_description, goal, task_id)
                    tool_name = selection.get("tool")
                    if not tool_name or tool_name == "none":
                        raise InvalidPlanError(
                            f"Plan step {index} not executable: no matching tool"
                        )
                    if not self.registry.get_tool(tool_name):
                        raise InvalidPlanError(
                            f"Plan step {index} not executable: tool '{tool_name}' not registered"
                        )

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
                self.state_manager.update_task(task_id, {
                    "status": "FAILED",
                    "error": str(e),
                    "failure_cause": "planning_invalid"
                })
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
            self.state_manager.update_task(task_id, {
                "status": "FAILED",
                "error": self.last_error,
                "failure_cause": "controller_error"
            })
            self.state_manager.archive_task(task_id, reason="error")
            return task_id
        finally:
            await self.llm.close()
