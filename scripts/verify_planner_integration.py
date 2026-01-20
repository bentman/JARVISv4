import asyncio
import json
import respx
from httpx import Response
from pathlib import Path
from backend.agents.planner.planner import PlannerAgent
from backend.core.llm.provider import OpenAIProvider
from backend.memory.working_state import WorkingStateManager

async def verify_task_file_creation():
    tasks_dir = Path("tasks_verify")
    tasks_dir.mkdir(exist_ok=True)
    
    state_manager = WorkingStateManager(base_path=tasks_dir)
    llm_provider = OpenAIProvider(model="test", base_url="http://mock-llm/v1")
    
    valid_plan = {
        "tasks": [
            {"id": "1", "description": "Step 1", "dependencies": [], "estimated_duration": "5m"},
            {"id": "2", "description": "Step 2", "dependencies": ["1"], "estimated_duration": "10m"},
            {"id": "3", "description": "Step 3", "dependencies": ["2"], "estimated_duration": "15m"}
        ]
    }
    
    async with respx.mock(base_url="http://mock-llm/v1") as respx_mock:
        respx_mock.post("/chat/completions").mock(return_value=Response(200, json={
            "choices": [{"message": {"content": json.dumps(valid_plan)}}]
        }))
        
        planner = PlannerAgent(llm_client=llm_provider, state_manager=state_manager)
        task_id = await planner.generate_plan(goal="Verify Task File Creation")
        
        task_file = tasks_dir / f"{task_id}.json"
        print(f"Checking for task file: {task_file}")
        
        if task_file.exists():
            print("✅ Task file created.")
            with open(task_file, "r") as f:
                data = json.load(f)
                print(f"Task status: {data['status']}")
                print(f"Goal: {data['goal']}")
                print(f"Steps count: {len(data['next_steps'])}")
                
                if data['goal'] == "Verify Task File Creation" and len(data['next_steps']) == 3:
                    print("✅ Data validation PASSED.")
                else:
                    print("❌ Data validation FAILED.")
        else:
            print("❌ Task file NOT created.")
            
    await llm_provider.close()

if __name__ == "__main__":
    asyncio.run(verify_task_file_creation())
