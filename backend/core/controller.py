import logging
import asyncio
import json
import time
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path

from backend.core.config.settings import Settings, load_settings
from backend.core.llm.provider import OpenAIProvider
from backend.memory.working_state import WorkingStateManager
from backend.agents.planner.planner import PlannerAgent, InvalidPlanError
from backend.agents.executor.executor import ExecutorAgent, EXECUTOR_SYSTEM_PROMPT
from backend.tools.registry.registry import ToolRegistry
from backend.tools.web_search import WebSearchTool
from backend.tools.text_output import TextOutputTool
from backend.tools.voice import VoiceSTTTool, VoiceTTSTool, VoiceWakeWordTool
from backend.memory.stores.trace_store import TraceStore
from backend.controller.engine.engine import WorkflowEngine
from backend.controller.engine.types import TaskContext, NodeType
from backend.controller.nodes.base import BaseNode

logger = logging.getLogger(__name__)

class SimpleToolNode(BaseNode):
    """Simple node that executes a single tool with predefined parameters."""
    
    def __init__(
        self,
        id: str,
        description: str,
        tool_name: str,
        tool_params: dict,
        registry: ToolRegistry,
        dependencies: Optional[List[str]] = None,
        executor: Optional[ExecutorAgent] = None
    ):
        super().__init__(id, NodeType.ROUTER, description)  # Use ROUTER type for tool execution
        self.tool_name = tool_name
        self.tool_params = tool_params
        self.registry = registry
        self.dependencies = dependencies or []
        self.executor = executor
    
    async def execute(self, context: TaskContext, results: dict) -> dict:
        """Execute the tool and return the result."""
        start_wall = time.monotonic()
        started_at = datetime.now().isoformat()
        if self.executor:
            try:
                result = await self.executor.execute_step(self.description, {
                    "tool": self.tool_name,
                    "params": self.tool_params
                })
                end_wall = time.monotonic()
                tool_name = result.get("tool") or self.tool_name
                tool_params = result.get("params") or self.tool_params
                status = result.get("status", "SUCCESS")
                error = result.get("error")
                if status == "FAILED":
                    return {
                        "tool_name": tool_name,
                        "tool_params": tool_params,
                        "status": "FAILED",
                        "error": error or "tool execution failed",
                        "started_at": started_at,
                        "completed_at": datetime.now().isoformat(),
                        "duration_ms_wall": (end_wall - start_wall) * 1000
                    }
                return {
                    "result": result,
                    "tool_name": tool_name,
                    "tool_params": tool_params,
                    "status": "SUCCESS",
                    "started_at": started_at,
                    "completed_at": datetime.now().isoformat(),
                    "duration_ms_wall": (end_wall - start_wall) * 1000
                }
            except Exception as exc:
                end_wall = time.monotonic()
                return {
                    "status": "FAILED",
                    "error": str(exc),
                    "tool": self.tool_name,
                    "params": self.tool_params,
                    "started_at": started_at,
                    "completed_at": datetime.now().isoformat(),
                    "duration_ms_wall": (end_wall - start_wall) * 1000
                }
        tool = self.registry.get_tool(self.tool_name)
        if not tool:
            raise Exception(f"Tool {self.tool_name} not found in registry")
        
        # Execute the tool with the predefined parameters
        try:
            result = await tool.execute(**self.tool_params)
            end_wall = time.monotonic()
            return {
                "node_id": self.id,
                "tool_name": self.tool_name,
                "tool_params": self.tool_params,
                "result": result,
                "status": "SUCCESS",
                "started_at": started_at,
                "completed_at": datetime.now().isoformat(),
                "duration_ms_wall": (end_wall - start_wall) * 1000
            }
        except Exception as e:
            end_wall = time.monotonic()
            return {
                "node_id": self.id,
                "tool_name": self.tool_name,
                "tool_params": self.tool_params,
                "result": None,
                "status": "FAILED",
                "error": str(e),
                "started_at": started_at,
                "completed_at": datetime.now().isoformat(),
                "duration_ms_wall": (end_wall - start_wall) * 1000
            }

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
        self.registry.register_tool(VoiceSTTTool())
        self.registry.register_tool(VoiceTTSTool())
        self.registry.register_tool(VoiceWakeWordTool())
        
        # Initialize Workflow Engine
        self.workflow_engine = WorkflowEngine()
        
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
        """Execute remaining steps for an existing task state using WorkflowEngine."""
        # Use WorkflowEngine to execute the remaining steps
        executed_steps = await self._execute_with_workflow_engine(task_id, goal, max_steps)
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
                    if isinstance(step, dict):
                        step["tool"] = tool_name
                        step["tool_params"] = selection.get("params", {})

                self.state_manager.update_task(task_id, {
                    "next_steps": planned_steps
                })

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

    async def _convert_plan_to_workflow_nodes(
        self,
        task_id: str,
        goal: str,
        use_executor: bool = True
    ) -> List[str]:
        """Convert plan steps to WorkflowEngine nodes and return node IDs."""
        task_state = self.state_manager.load_task(task_id)
        next_steps = task_state.get("next_steps", [])
        node_ids = []
        id_mapping: Dict[str, str] = {}
        for index, step in enumerate(next_steps):
            if not isinstance(step, dict):
                continue
            step_id = str(step.get("id")) if step.get("id") is not None else None
            tool_name = step.get("tool")
            if not tool_name:
                tool_name = "unknown"
            if step_id:
                id_mapping[step_id] = f"step_{index}_{tool_name}"
        
        for index, step in enumerate(next_steps):
            step_description = step.get("description") if isinstance(step, dict) else None
            if not step_description:
                continue
                
            # Select tool for this step
            tool_name = step.get("tool") if isinstance(step, dict) else None
            tool_params = step.get("tool_params") if isinstance(step, dict) else None
            if not tool_name:
                selection = await self._select_tool_for_step(step_description, goal, task_id)
                tool_name = selection.get("tool")
                tool_params = selection.get("params", {})
            if tool_params is None:
                tool_params = {}
            
            if not tool_name or tool_name == "none":
                logger.warning(f"Step {index} not executable: no matching tool")
                continue
                
            # Create a simple node that executes the tool
            node_id = f"step_{index}_{tool_name}"
            dependencies = []
            for dep in step.get("dependencies", []):
                dep_key = str(dep)
                if dep_key in id_mapping:
                    dependencies.append(id_mapping[dep_key])
            node = SimpleToolNode(
                id=node_id,
                description=step_description,
                tool_name=tool_name,
                tool_params=tool_params,
                registry=self.registry,
                dependencies=dependencies,
                executor=self.executor if use_executor else None
            )
            self.workflow_engine.add_node(node)
            node_ids.append(node_id)
            
        return node_ids

    async def _execute_with_workflow_engine(
        self,
        task_id: str,
        goal: str,
        max_steps: Optional[int] = None,
        use_executor: bool = True
    ) -> int:
        """Execute remaining steps using WorkflowEngine."""
        # Convert plan steps to workflow nodes
        node_ids = await self._convert_plan_to_workflow_nodes(task_id, goal, use_executor=use_executor)
        if not node_ids:
            logger.info("No executable steps found for workflow engine")
            return 0
            
        # Create TaskContext for workflow execution
        context = TaskContext(
            memory_store=None,  # Not used in this phase
            tool_registry=self.registry,
            data={
                "task_id": task_id,
                "goal": goal,
                "workflow_id": f"workflow_{task_id}",
                "start_time": None  # Will be set by WorkflowEngine
            }
        )
        
        # Execute workflow
        result = await self.workflow_engine.execute_workflow(context)
        
        if result["status"] == "completed":
            # Update task state based on workflow results
            executed_steps = len(node_ids)
            try:
                for index, node_id in enumerate(node_ids):
                    if max_steps is not None and index >= max_steps:
                        break
                    if index >= self.MAX_EXECUTED_STEPS:
                        raise RuntimeError(
                            f"MAX_EXECUTED_STEPS exceeded: {self.MAX_EXECUTED_STEPS}"
                        )
                        
                    # Get result for this node
                    node_result = result.get("results", {}).get(node_id, {})
                    tool_name = node_result.get("tool_name") or node_result.get("tool") or "unknown"
                    tool_params = node_result.get("tool_params") or node_result.get("params") or {}
                    status = node_result.get("status", "SUCCESS")
                    error = node_result.get("error")
                    if status == "FAILED":
                        if tool_name == "none":
                            raise RuntimeError("execution_step_failed: no_tool")
                        raise RuntimeError(error or "tool execution failed")
                    result_payload = node_result.get("result")
                    resolved_payload = result_payload
                    if isinstance(result_payload, dict) and {"result", "status", "tool"}.issubset(result_payload.keys()):
                        resolved_payload = result_payload.get("result")
                    artifact = resolved_payload
                    if not isinstance(resolved_payload, dict):
                        artifact = str(resolved_payload) if resolved_payload is not None else ""
                    
                    # Update task state
                    task_state = self.state_manager.load_task(task_id)
                    next_steps = task_state.get("next_steps", [])
                    step_description = None
                    if index < len(next_steps):
                        step_description = next_steps[index].get("description") if isinstance(next_steps[index], dict) else None
                    self.state_manager.update_task(task_id, {
                        "current_step": {
                            "index": index,
                            "description": step_description
                        }
                    })
                    self.trace_store.append_tool_call(
                        task_id=task_id,
                        step_index=index,
                        tool_name=tool_name,
                        params=tool_params,
                        status=status,
                        result=str(node_result.get("result")) if node_result.get("result") is not None else None,
                        error=error
                    )
                    duration_ms_tool = None
                    if isinstance(resolved_payload, dict):
                        duration_ms_tool = resolved_payload.get("duration_ms")
                    self.state_manager.complete_step(
                        task_id,
                        step_index=index,
                        outcome="SUCCESS",
                        artifact=artifact,
                        tool_name=tool_name,
                        tool_params=tool_params,
                        started_at=node_result.get("started_at"),
                        completed_at=node_result.get("completed_at"),
                        duration_ms_tool=duration_ms_tool,
                        duration_ms_wall=node_result.get("duration_ms_wall")
                    )
                    
                    # Update next_steps to remove completed step
                    task_state = self.state_manager.load_task(task_id)
                    next_steps = task_state.get("next_steps", [])
                    if next_steps:
                        self.state_manager.update_task(task_id, {
                            "next_steps": next_steps[1:]
                        })
            except RuntimeError as exc:
                error_msg = str(exc)
                logger.error(f"Workflow failed: {error_msg}")
                self.last_error = error_msg
                if error_msg.startswith("execution_step_failed") or "MAX_EXECUTED_STEPS" in error_msg:
                    self.state_manager.update_task(task_id, {
                        "status": "FAILED",
                        "error": self.last_error,
                        "failure_cause": "execution_step_failed"
                    })
                    self.state_manager.archive_task(task_id, reason="failed_execute")
                else:
                    self.state_manager.update_task(task_id, {
                        "status": "FAILED",
                        "error": self.last_error,
                        "failure_cause": "controller_error"
                    })
                    self.state_manager.archive_task(task_id, reason="error")
                self.state = ControllerState.FAILED
                return 0

            return executed_steps
        else:
            # Workflow failed
            error_msg = result.get("error", "Workflow execution failed")
            logger.error(f"Workflow failed: {error_msg}")
            self.last_error = error_msg
            self.state_manager.update_task(task_id, {
                "status": "FAILED",
                "error": self.last_error,
                "failure_cause": "execution_step_failed"
            })
            self.state_manager.archive_task(task_id, reason="failed_execute")
            self.state = ControllerState.FAILED
            return 0

    async def run_voice_lifecycle(
        self,
        audio_file_path: str,
        threshold: float = 0.5,
        stt_model: str = "base",
        stt_language: Optional[str] = None,
        tts_voice: str = "default",
        agent_text: str = "voice_response"
    ) -> str:
        """
        Execute the canonical voice lifecycle using deterministic, fixed steps.
        Orchestration-only: uses existing tools verbatim and archives the result.
        """
        self.last_error = None
        self.state = ControllerState.EXECUTING

        stt_params: Dict[str, Any] = {
            "audio_file_path": audio_file_path,
            "model": stt_model
        }
        if stt_language is not None:
            stt_params["language"] = stt_language

        next_steps = [
            {
                "description": "Detect wake word from captured audio",
                "tool": "voice_wake_word",
                "tool_params": {
                    "audio_file_path": audio_file_path,
                    "threshold": threshold
                }
            },
            {
                "description": "Transcribe captured audio to text",
                "tool": "voice_stt",
                "tool_params": stt_params
            },
            {
                "description": "Agent execution (deterministic text output)",
                "tool": "text_output",
                "tool_params": {
                    "text": agent_text
                }
            },
            {
                "description": "Synthesize speech from agent output",
                "tool": "voice_tts",
                "tool_params": {
                    "text": "--help",
                    "voice": tts_voice
                }
            }
        ]

        task_id = self.state_manager.create_task({
            "goal": "voice_lifecycle",
            "domain": "voice",
            "constraints": ["deterministic"],
            "next_steps": next_steps
        })

        await self._execute_with_workflow_engine(
            task_id,
            goal="voice_lifecycle",
            use_executor=False
        )

        archive_path: Optional[Path] = None
        if self.state != ControllerState.FAILED:
            self.state = ControllerState.ARCHIVING
            logger.info(f"Transitioning to {self.state.value}")
            self.state_manager.update_task(task_id, {"status": "COMPLETED"})
            archive_path = self.state_manager.archive_task(task_id)
            self.state = ControllerState.COMPLETED
            logger.info(f"Voice lifecycle {task_id} COMPLETED and ARCHIVED.")
        else:
            logger.error(f"Voice lifecycle {task_id} halted in FAILED state.")
            try:
                archive_path = self.state_manager.find_archived_task_path(task_id)
            except FileNotFoundError:
                archive_path = None

        if archive_path:
            session_path = self._write_voice_session(task_id, archive_path)
            self._write_voice_session_metrics(session_path, archive_path)

        return task_id

    def _build_voice_session(
        self,
        task_id: str,
        archive_path: Path,
        task_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        completed_steps = task_state.get("completed_steps", [])
        step_entries: List[Tuple[str, int]] = []
        for step in completed_steps:
            tool_name = step.get("tool_name") or "unknown"
            index = step.get("index")
            if index is None:
                continue
            step_key = tool_name
            if any(existing[0] == step_key for existing in step_entries):
                step_key = f"{tool_name}_{index}"
            step_entries.append((step_key, index))

        created_at = task_state.get("metadata", {}).get("created_at")
        completed_at = None
        if completed_steps:
            completed_at = completed_steps[-1].get("completed_at")

        return {
            "session_id": f"voice_session_{task_id}",
            "task_id": task_id,
            "status": task_state.get("status"),
            "failure_cause": task_state.get("failure_cause"),
            "created_at": created_at,
            "completed_at": completed_at,
            "step_order": [entry[0] for entry in step_entries],
            "step_artifacts": {
                entry[0]: {
                    "archive_path": str(archive_path),
                    "completed_step_index": entry[1]
                }
                for entry in step_entries
            }
        }

    def _write_voice_session(self, task_id: str, archive_path: Path) -> Path:
        task_state = json.loads(archive_path.read_text())
        archive_dir = archive_path.parent
        session = self._build_voice_session(task_id, archive_path, task_state)
        return self.state_manager.write_voice_session(session, archive_dir)

    def _write_voice_session_metrics(self, session_path: Path, archive_path: Path) -> Path:
        session = json.loads(session_path.read_text())
        task_state = json.loads(archive_path.read_text())
        session_id = session.get("session_id")
        if not session_id:
            raise ValueError("VoiceSession metrics missing session_id")

        created_at = session.get("created_at")
        completed_at = session.get("completed_at")
        session_duration_ms = None
        if created_at and completed_at:
            try:
                start = datetime.fromisoformat(created_at)
                end = datetime.fromisoformat(completed_at)
                session_duration_ms = (end - start).total_seconds() * 1000
            except ValueError:
                session_duration_ms = None

        completed_steps = task_state.get("completed_steps", [])
        step_metrics: List[Dict[str, Any]] = []
        for step_key in session.get("step_order", []):
            entry = session.get("step_artifacts", {}).get(step_key)
            if not entry:
                continue
            step_index = entry.get("completed_step_index")
            if not isinstance(step_index, int) or step_index >= len(completed_steps):
                continue
            step_state = completed_steps[step_index]
            tool_name = step_state.get("tool_name")
            tool_params = step_state.get("tool_params", {}) or {}
            duration_ms_tool = step_state.get("duration_ms_tool")
            duration_ms_wall = step_state.get("duration_ms_wall")

            step_metrics.append({
                "step_name": step_key,
                "tool_name": tool_name,
                "status": step_state.get("outcome"),
                "duration_ms_tool": duration_ms_tool,
                "duration_ms_wall": duration_ms_wall,
                "tool_params": tool_params,
            })

        metrics = {
            "session_id": session_id,
            "task_id": session.get("task_id"),
            "status": session.get("status"),
            "failure_cause": session.get("failure_cause"),
            "session_duration_ms": session_duration_ms,
            "steps": step_metrics,
        }

        return self.state_manager.write_voice_session_metrics(session_id, metrics, archive_path.parent)

    def replay_voice_session(self, session_id: str) -> Dict[str, Any]:
        """Validate a VoiceSession artifact without re-executing tools."""
        session = self.state_manager.load_voice_session(session_id)
        step_order = session.get("step_order", [])
        step_artifacts = session.get("step_artifacts", {})
        errors: List[str] = []

        for step_key in step_order:
            entry = step_artifacts.get(step_key)
            if not entry:
                errors.append(f"Missing artifact reference for {step_key}")
                continue
            archive_path = entry.get("archive_path")
            step_index = entry.get("completed_step_index")
            if archive_path is None or step_index is None:
                errors.append(f"Invalid artifact reference for {step_key}")
                continue
            archive_file = Path(archive_path)
            if not archive_file.exists():
                errors.append(f"Archive file missing for {step_key}: {archive_path}")
                continue
            task_state = json.loads(archive_file.read_text())
            completed_steps = task_state.get("completed_steps", [])
            if not isinstance(step_index, int) or step_index >= len(completed_steps):
                errors.append(f"Completed step index invalid for {step_key}: {step_index}")
                continue
            recorded_tool = completed_steps[step_index].get("tool_name")
            expected_tool = step_key
            suffix = f"_{step_index}"
            if step_key.endswith(suffix):
                expected_tool = step_key[: -len(suffix)]
            if recorded_tool != expected_tool:
                errors.append(
                    f"Tool mismatch for {step_key}: recorded={recorded_tool} expected={expected_tool}"
                )

        status = "COMPLETED" if not errors else "FAILED"
        return {
            "session_id": session_id,
            "status": status,
            "errors": errors,
            "validated_steps": len(step_order) if not errors else 0
        }

    async def run_research_lifecycle(
        self,
        query: str,
        synthesis_text: str,
        provider: str = "duckduckgo",
        max_results: int = 5
    ) -> str:
        """
        Execute the canonical research lifecycle using deterministic, fixed steps.
        Orchestration-only: uses existing tools verbatim and archives the result.
        """
        self.last_error = None
        self.state = ControllerState.EXECUTING

        next_steps = [
            {
                "description": "Search the web for external research inputs",
                "tool": "web_search",
                "tool_params": {
                    "query": query,
                    "provider": provider,
                    "max_results": max_results
                }
            },
            {
                "description": "Persist deterministic research synthesis",
                "tool": "text_output",
                "tool_params": {
                    "text": synthesis_text
                }
            }
        ]

        task_id = self.state_manager.create_task({
            "goal": "research_lifecycle",
            "domain": "research",
            "constraints": ["deterministic"],
            "next_steps": next_steps
        })

        await self._execute_with_workflow_engine(
            task_id,
            goal="research_lifecycle",
            use_executor=False
        )

        task_state = self.state_manager.load_task(task_id)
        completed_steps = task_state.get("completed_steps", [])
        for step in completed_steps:
            if step.get("tool_name") != "web_search":
                continue
            raw_result = step.get("artifact")
            step["artifact"] = {
                "query": query,
                "provider": provider,
                "max_results": max_results,
                "result": raw_result
            }
        if completed_steps:
            self.state_manager.update_task(task_id, {"completed_steps": completed_steps})

        archive_path: Optional[Path] = None
        if self.state != ControllerState.FAILED:
            self.state = ControllerState.ARCHIVING
            logger.info(f"Transitioning to {self.state.value}")
            self.state_manager.update_task(task_id, {"status": "COMPLETED"})
            archive_path = self.state_manager.archive_task(task_id)
            self.state = ControllerState.COMPLETED
            logger.info(f"Research lifecycle {task_id} COMPLETED and ARCHIVED.")
        else:
            logger.error(f"Research lifecycle {task_id} halted in FAILED state.")
            try:
                archive_path = self.state_manager.find_archived_task_path(task_id)
            except FileNotFoundError:
                archive_path = None

        if archive_path:
            self._write_research_session(task_id, archive_path)

        return task_id

    def _build_research_session(
        self,
        task_id: str,
        archive_path: Path,
        task_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        completed_steps = task_state.get("completed_steps", [])
        step_entries: List[Tuple[str, int]] = []
        for step in completed_steps:
            tool_name = step.get("tool_name") or "unknown"
            index = step.get("index")
            if index is None:
                continue
            step_key = tool_name
            if any(existing[0] == step_key for existing in step_entries):
                step_key = f"{tool_name}_{index}"
            step_entries.append((step_key, index))

        created_at = task_state.get("metadata", {}).get("created_at")
        completed_at = None
        if completed_steps:
            completed_at = completed_steps[-1].get("completed_at")

        return {
            "session_id": f"research_session_{task_id}",
            "task_id": task_id,
            "status": task_state.get("status"),
            "failure_cause": task_state.get("failure_cause"),
            "created_at": created_at,
            "completed_at": completed_at,
            "step_order": [entry[0] for entry in step_entries],
            "step_artifacts": {
                entry[0]: {
                    "archive_path": str(archive_path),
                    "completed_step_index": entry[1]
                }
                for entry in step_entries
            }
        }

    def _write_research_session(self, task_id: str, archive_path: Path) -> Path:
        task_state = json.loads(archive_path.read_text())
        archive_dir = archive_path.parent
        session = self._build_research_session(task_id, archive_path, task_state)
        return self.state_manager.write_research_session(session, archive_dir)

    def replay_research_session(self, session_id: str) -> Dict[str, Any]:
        """Validate a ResearchSession artifact without re-executing tools."""
        session = self.state_manager.load_research_session(session_id)
        step_order = session.get("step_order", [])
        step_artifacts = session.get("step_artifacts", {})
        errors: List[str] = []

        for step_key in step_order:
            entry = step_artifacts.get(step_key)
            if not entry:
                errors.append(f"Missing artifact reference for {step_key}")
                continue
            archive_path = entry.get("archive_path")
            step_index = entry.get("completed_step_index")
            if archive_path is None or step_index is None:
                errors.append(f"Invalid artifact reference for {step_key}")
                continue
            archive_file = Path(archive_path)
            if not archive_file.exists():
                errors.append(f"Archive file missing for {step_key}: {archive_path}")
                continue
            task_state = json.loads(archive_file.read_text())
            completed_steps = task_state.get("completed_steps", [])
            if not isinstance(step_index, int) or step_index >= len(completed_steps):
                errors.append(f"Completed step index invalid for {step_key}: {step_index}")
                continue
            recorded_tool = completed_steps[step_index].get("tool_name")
            expected_tool = step_key
            suffix = f"_{step_index}"
            if step_key.endswith(suffix):
                expected_tool = step_key[: -len(suffix)]
            if recorded_tool != expected_tool:
                errors.append(
                    f"Tool mismatch for {step_key}: recorded={recorded_tool} expected={expected_tool}"
                )

        status = "COMPLETED" if not errors else "FAILED"
        return {
            "session_id": session_id,
            "status": status,
            "errors": errors,
            "validated_steps": len(step_order) if not errors else 0
        }

    async def run_conversation_lifecycle(
        self,
        turns: List[Dict[str, str]]
    ) -> str:
        """
        Execute the canonical conversation lifecycle using deterministic, fixed steps.
        Orchestration-only: uses existing tools verbatim and archives the result.
        """
        self.last_error = None
        self.state = ControllerState.EXECUTING

        next_steps: List[Dict[str, Any]] = []
        for index, turn in enumerate(turns):
            user_text = turn.get("user")
            assistant_text = turn.get("assistant")
            if user_text is None or assistant_text is None:
                raise ValueError("Each turn must include 'user' and 'assistant' text")

            next_steps.extend([
                {
                    "description": f"Persist conversation user turn {index}",
                    "tool": "text_output",
                    "tool_params": {
                        "text": user_text
                    }
                },
                {
                    "description": f"Persist conversation assistant turn {index}",
                    "tool": "text_output",
                    "tool_params": {
                        "text": assistant_text
                    }
                }
            ])

        task_id = self.state_manager.create_task({
            "goal": "conversation_lifecycle",
            "domain": "conversation",
            "constraints": ["deterministic"],
            "next_steps": next_steps
        })

        await self._execute_with_workflow_engine(
            task_id,
            goal="conversation_lifecycle",
            use_executor=False
        )

        archive_path: Optional[Path] = None
        if self.state != ControllerState.FAILED:
            self.state = ControllerState.ARCHIVING
            logger.info(f"Transitioning to {self.state.value}")
            self.state_manager.update_task(task_id, {"status": "COMPLETED"})
            archive_path = self.state_manager.archive_task(task_id)
            self.state = ControllerState.COMPLETED
            logger.info(f"Conversation lifecycle {task_id} COMPLETED and ARCHIVED.")
        else:
            logger.error(f"Conversation lifecycle {task_id} halted in FAILED state.")
            try:
                archive_path = self.state_manager.find_archived_task_path(task_id)
            except FileNotFoundError:
                archive_path = None

        if archive_path:
            self._write_conversation_session(task_id, archive_path)

        return task_id

    def _build_conversation_session(
        self,
        task_id: str,
        archive_path: Path,
        task_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        completed_steps = task_state.get("completed_steps", [])
        step_entries: List[Tuple[str, int]] = []
        for step in completed_steps:
            index = step.get("index")
            if index is None:
                continue
            turn_index = index // 2
            role = "user" if index % 2 == 0 else "assistant"
            step_key = f"turn_{turn_index}_{role}"
            if any(existing[0] == step_key for existing in step_entries):
                step_key = f"{step_key}_{index}"
            step_entries.append((step_key, index))

        created_at = task_state.get("metadata", {}).get("created_at")
        completed_at = None
        if completed_steps:
            completed_at = completed_steps[-1].get("completed_at")

        return {
            "session_id": f"conversation_session_{task_id}",
            "task_id": task_id,
            "status": task_state.get("status"),
            "failure_cause": task_state.get("failure_cause"),
            "created_at": created_at,
            "completed_at": completed_at,
            "step_order": [entry[0] for entry in step_entries],
            "step_artifacts": {
                entry[0]: {
                    "archive_path": str(archive_path),
                    "completed_step_index": entry[1]
                }
                for entry in step_entries
            }
        }

    def _write_conversation_session(self, task_id: str, archive_path: Path) -> Path:
        task_state = json.loads(archive_path.read_text())
        archive_dir = archive_path.parent
        session = self._build_conversation_session(task_id, archive_path, task_state)
        return self.state_manager.write_conversation_session(session, archive_dir)

    def replay_conversation_session(self, session_id: str) -> Dict[str, Any]:
        """Validate a ConversationSession artifact without re-executing tools."""
        session = self.state_manager.load_conversation_session(session_id)
        step_order = session.get("step_order", [])
        step_artifacts = session.get("step_artifacts", {})
        errors: List[str] = []

        for step_key in step_order:
            entry = step_artifacts.get(step_key)
            if not entry:
                errors.append(f"Missing artifact reference for {step_key}")
                continue
            archive_path = entry.get("archive_path")
            step_index = entry.get("completed_step_index")
            if archive_path is None or step_index is None:
                errors.append(f"Invalid artifact reference for {step_key}")
                continue
            archive_file = Path(archive_path)
            if not archive_file.exists():
                errors.append(f"Archive file missing for {step_key}: {archive_path}")
                continue
            task_state = json.loads(archive_file.read_text())
            completed_steps = task_state.get("completed_steps", [])
            if not isinstance(step_index, int) or step_index >= len(completed_steps):
                errors.append(f"Completed step index invalid for {step_key}: {step_index}")
                continue
            recorded_tool = completed_steps[step_index].get("tool_name")
            if recorded_tool != "text_output":
                errors.append(
                    f"Tool mismatch for {step_key}: recorded={recorded_tool} expected=text_output"
                )

        status = "COMPLETED" if not errors else "FAILED"
        return {
            "session_id": session_id,
            "status": status,
            "errors": errors,
            "validated_steps": len(step_order) if not errors else 0
        }
