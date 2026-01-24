import json
import logging
from typing import Any, Dict, List, Optional, Set
from backend.memory.working_state import WorkingStateManager
from backend.core.llm.base import BaseLLMProvider

logger = logging.getLogger(__name__)

class InvalidPlanError(Exception):
    """Raised when the generated plan is invalid (e.g., circular dependencies)."""
    pass

SYSTEM_PROMPT = """You are a task planning specialist. Your ONLY job is to decompose goals into sub-tasks.

Rules:
- Each task must be independently verifiable.
- Tasks must form a valid Directed Acyclic Graph (DAG).
- Circular dependencies are strictly forbidden.
- Dependencies in the 'dependencies' list MUST refer to the 'id' of previous tasks in the same list.
- Be specific: "set up environment" is too vague.
- Use concrete deliverables: files, endpoints, tests.
- Estimate dependencies accurately.

Output Format: JSON only, no explanations.
Structure:
{
  "tasks": [
    {
      "id": "1",
      "description": "...",
      "dependencies": [],
      "estimated_duration": "..."
    }
  ]
}"""

class PlannerAgent:
    """
    Decomposes high-level goals into executable sub-tasks.
    Stateless reasoning component focused on strategic decomposition.
    """
    
    def __init__(self, llm_client: BaseLLMProvider, state_manager: WorkingStateManager):
        self.llm = llm_client
        self.state_manager = state_manager
        self.system_prompt = SYSTEM_PROMPT

    async def generate_plan(
        self,
        goal: str,
        constraints: Optional[List[str]] = None,
        domain: str = "general",
        task_id: Optional[str] = None
    ) -> str:
        """
        Decomposes a goal into a structured plan and persists it.
        
        Args:
            goal: The high-level objective.
            constraints: Optional list of constraints.
            domain: The task domain (default: general).
            
        Returns:
            task_id: The ID of the created task state.
            
        Raises:
            InvalidPlanError: If the plan fails validation or contains cycles.
        """
        prompt = self._build_prompt(goal, constraints, domain)
        
        response = await self.llm.generate(prompt)
        plan = self._parse_response(response)
        
        # Validate plan structure and DAG properties
        self._validate_plan(plan)
        
        # Persist to Tier 1 Working State
        if task_id is None:
            task_id = self.state_manager.create_task({
                "goal": goal,
                "domain": domain,
                "constraints": constraints or [],
                "next_steps": plan["tasks"]
            })
        else:
            self.state_manager.update_task(task_id, {
                "domain": domain,
                "constraints": constraints or [],
                "next_steps": plan["tasks"]
            })
        
        logger.info(f"Generated plan for goal '{goal}' with task_id {task_id}")
        return task_id

    def _build_prompt(self, goal: str, constraints: Optional[List[str]], domain: str) -> str:
        constraints_str = "\n".join([f"- {c}" for c in constraints]) if constraints else "None"
        return f"""{self.system_prompt}

Goal: {goal}
Domain: {domain}
Constraints:
{constraints_str}

Decompose this goal into concrete sub-tasks. Output JSON only."""

    def _parse_response(self, response: str) -> Dict[str, Any]:
        """Extract JSON from LLM response."""
        try:
            # Handle potential markdown fencing
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                response = response.split("```")[1].split("```")[0].strip()
            
            return json.loads(response)
        except (json.JSONDecodeError, IndexError) as e:
            raise InvalidPlanError(f"Failed to parse LLM response as JSON: {str(e)}")

    def _validate_plan(self, plan: Dict[str, Any]) -> None:
        """Perform schema and DAG validation."""
        if "tasks" not in plan or not isinstance(plan["tasks"], list):
            raise InvalidPlanError("Plan missing 'tasks' list")
            
        tasks = plan["tasks"]
        if not tasks:
            raise InvalidPlanError("Plan contains no tasks")

        task_ids = {str(t.get("id")) for t in tasks}
        
        # Check for cycles
        adj = {str(t.get("id")): [str(d) for d in t.get("dependencies", [])] for t in tasks}
        
        # Verify all dependencies exist
        for tid, deps in adj.items():
            for dep in deps:
                if dep not in task_ids:
                    raise InvalidPlanError(f"Task {tid} depends on non-existent task {dep}")

        # Cycle detection using DFS
        visited = set()
        path = set()

        def has_cycle(v: str) -> bool:
            visited.add(v)
            path.add(v)
            for neighbor in adj.get(v, []):
                if neighbor not in visited:
                    if has_cycle(neighbor):
                        return True
                elif neighbor in path:
                    return True
            path.remove(v)
            return False

        for tid in task_ids:
            if tid not in visited:
                if has_cycle(tid):
                    raise InvalidPlanError("Plan contains circular dependencies")

    def _is_valid_dag(self, plan: Dict[str, Any]) -> bool:
        """Utility method for checking DAG status (reuses validation logic)."""
        try:
            self._validate_plan(plan)
            return True
        except InvalidPlanError:
            return False
