import pytest
import json
import respx
from httpx import Response
from pathlib import Path
from backend.agents.planner.planner import PlannerAgent, InvalidPlanError
from backend.core.llm.provider import OpenAIProvider
from backend.memory.working_state import WorkingStateManager

@pytest.fixture
def llm_provider():
    # Real provider with dummy config
    return OpenAIProvider(model="test-model", api_key="test-key", base_url="http://mock-llm:11434/v1")

@pytest.fixture
def state_manager(tmp_path):
    manager = WorkingStateManager(base_path=tmp_path)
    return manager

@pytest.mark.asyncio
async def test_planner_generate_plan_success(llm_provider, state_manager):
    valid_plan = {
        "tasks": [
            {"id": "1", "description": "Task 1", "dependencies": [], "estimated_duration": "10m"},
            {"id": "2", "description": "Task 2", "dependencies": ["1"], "estimated_duration": "20m"}
        ]
    }
    
    async with respx.mock(base_url="http://mock-llm:11434/v1") as respx_mock:
        respx_mock.post("/chat/completions").mock(return_value=Response(200, json={
            "choices": [{"message": {"content": json.dumps(valid_plan)}}]
        }))
        
        planner = PlannerAgent(llm_client=llm_provider, state_manager=state_manager)
        task_id = await planner.generate_plan(goal="Test Goal", constraints=["constraint 1"])
        
        assert task_id.startswith("task_")
        
        # Verify state was saved
        state = state_manager.load_task(task_id)
        assert state["goal"] == "Test Goal"
        assert len(state["next_steps"]) == 2
        assert state["next_steps"][0]["id"] == "1"
    
    await llm_provider.close()

@pytest.mark.asyncio
async def test_planner_cycle_detection(llm_provider, state_manager):
    circular_plan = {
        "tasks": [
            {"id": "1", "description": "Task 1", "dependencies": ["2"], "estimated_duration": "10m"},
            {"id": "2", "description": "Task 2", "dependencies": ["1"], "estimated_duration": "20m"}
        ]
    }
    
    async with respx.mock(base_url="http://mock-llm:11434/v1") as respx_mock:
        respx_mock.post("/chat/completions").mock(return_value=Response(200, json={
            "choices": [{"message": {"content": json.dumps(circular_plan)}}]
        }))
        
        planner = PlannerAgent(llm_client=llm_provider, state_manager=state_manager)
        
        with pytest.raises(InvalidPlanError, match="circular dependencies"):
            await planner.generate_plan(goal="Cycle Test")
            
    await llm_provider.close()

@pytest.mark.asyncio
async def test_planner_missing_dependency(llm_provider, state_manager):
    broken_plan = {
        "tasks": [
            {"id": "1", "description": "Task 1", "dependencies": ["99"], "estimated_duration": "10m"}
        ]
    }
    
    async with respx.mock(base_url="http://mock-llm:11434/v1") as respx_mock:
        respx_mock.post("/chat/completions").mock(return_value=Response(200, json={
            "choices": [{"message": {"content": json.dumps(broken_plan)}}]
        }))
        
        planner = PlannerAgent(llm_client=llm_provider, state_manager=state_manager)
        
        with pytest.raises(InvalidPlanError, match="non-existent task 99"):
            await planner.generate_plan(goal="Broken Dep Test")
            
    await llm_provider.close()

@pytest.mark.asyncio
async def test_planner_invalid_json(llm_provider, state_manager):
    async with respx.mock(base_url="http://mock-llm:11434/v1") as respx_mock:
        respx_mock.post("/chat/completions").mock(return_value=Response(200, json={
            "choices": [{"message": {"content": "Not a JSON string"}}]
        }))
        
        planner = PlannerAgent(llm_client=llm_provider, state_manager=state_manager)
        
        with pytest.raises(InvalidPlanError, match="Failed to parse LLM response"):
            await planner.generate_plan(goal="JSON Failure Test")
            
    await llm_provider.close()

@pytest.mark.asyncio
async def test_planner_markdown_parsing(llm_provider, state_manager):
    valid_plan = {
        "tasks": [
            {"id": "1", "description": "Task 1", "dependencies": [], "estimated_duration": "10m"}
        ]
    }
    
    async with respx.mock(base_url="http://mock-llm:11434/v1") as respx_mock:
        respx_mock.post("/chat/completions").mock(return_value=Response(200, json={
            "choices": [{"message": {"content": f"```json\n{json.dumps(valid_plan)}\n```"}}]
        }))
        
        planner = PlannerAgent(llm_client=llm_provider, state_manager=state_manager)
        task_id = await planner.generate_plan(goal="Markdown Test")
        
        state = state_manager.load_task(task_id)
        assert len(state["next_steps"]) == 1
        
    await llm_provider.close()
