from fastapi import FastAPI, HTTPException

from backend.api.models import TaskRequest, TaskResponse
from backend.core.controller import ECFController

app = FastAPI(title="JARVISv4 API", version="0.1.0")


@app.post("/v1/tasks", response_model=TaskResponse)
async def create_task(payload: TaskRequest) -> TaskResponse:
    if not payload.goal.strip():
        raise HTTPException(status_code=400, detail="goal must be non-empty")

    controller = ECFController()
    task_id = await controller.run_task(payload.goal)
    error = controller.last_error if controller.state.value == "FAILED" else None

    return TaskResponse(task_id=task_id, state=controller.state.value, error=error)