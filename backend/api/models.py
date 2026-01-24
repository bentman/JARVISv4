from typing import Optional

from pydantic import BaseModel, Field


class TaskRequest(BaseModel):
    goal: str = Field(..., min_length=1)


class TaskResponse(BaseModel):
    task_id: str
    state: str
    error: Optional[str] = None