import json
import logging
from typing import Any, Dict, List, Optional
from backend.core.llm.base import BaseLLMProvider
from backend.tools.registry.registry import ToolRegistry

logger = logging.getLogger(__name__)

EXECUTOR_SYSTEM_PROMPT = """You are a precise execution agent for JARVISv4. 
Your task is to select the most appropriate tool to accomplish the given step and provide the necessary parameters.

Rules:
1. Select ONLY ONE tool from the provided list.
2. Provide parameters exactly as specified in the tool's JSON Schema.
3. If NO tool in the list can accomplish the task, respond with: {{"tool": "none", "rationale": "Reason why no tool matches"}}.
4. Output JSON only, no conversational filler.

Available Tools:
{tool_definitions}

Output Format:
{{
  "tool": "tool_name",
  "params": {{ ... }},
  "rationale": "One sentence explaining choice"
}}"""

class ExecutorAgent:
    """
    Tactical agent responsible for converting task steps into tool invocations.
    Stateless reasoning component focused on tool selection and parameterization.
    """
    
    def __init__(self, llm_client: BaseLLMProvider, registry: ToolRegistry):
        self.llm = llm_client
        self.registry = registry

    async def execute_step(self, step_description: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Processes a single step, selects a tool, and executes it.
        
        Returns:
            A dict containing the execution result, tool used, and status.
        """
        tool_defs = self.registry.get_tool_definitions()
        
        prompt = EXECUTOR_SYSTEM_PROMPT.format(
            tool_definitions=json.dumps(tool_defs, indent=2)
        )
        
        user_prompt = f"Task Step: {step_description}\nContext: {json.dumps(context or {})}"
        
        full_prompt = f"{prompt}\n\n{user_prompt}"
        
        response = await self.llm.generate(full_prompt)
        selection = self._parse_response(response)
        
        tool_name = selection.get("tool")
        params = selection.get("params", {})
        
        if tool_name == "none" or not tool_name:
            logger.warning(f"Executor could not find a tool for step: {step_description}")
            return {
                "status": "FAILED",
                "error": f"No suitable tool found: {selection.get('rationale', 'Unknown reason')}",
                "tool": "none"
            }
            
        try:
            result = await self.registry.call_tool(tool_name, **params)
            return {
                "status": "SUCCESS",
                "result": result,
                "tool": tool_name,
                "params": params
            }
        except Exception as e:
            logger.error(f"Execution failed for tool {tool_name}: {str(e)}")
            return {
                "status": "FAILED",
                "error": str(e),
                "tool": tool_name,
                "params": params
            }

    def _parse_response(self, response: str) -> Dict[str, Any]:
        """Extract JSON from LLM response."""
        try:
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                response = response.split("```")[1].split("```")[0].strip()
            
            return json.loads(response)
        except (json.JSONDecodeError, IndexError):
            # Fallback if LLM fails to provide valid JSON
            logger.error(f"Failed to parse LLM response in Executor: {response}")
            return {"tool": "none", "rationale": "Invalid response format from LLM"}
