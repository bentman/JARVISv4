from typing import Optional

from pydantic import BaseModel, Field


class TaskRequest(BaseModel):
    goal: str = Field(..., min_length=1)


class TaskResponse(BaseModel):
    task_id: str
    state: str
    error: Optional[str] = None


class VoiceSTTRequest(BaseModel):
    audio_file_path: str = Field(..., min_length=1)
    model: Optional[str] = None
    language: Optional[str] = None


class VoiceTTSRequest(BaseModel):
    text: str = Field(..., min_length=1)
    voice: Optional[str] = None


class VoiceWakeWordRequest(BaseModel):
    audio_file_path: str = Field(..., min_length=1)
    threshold: Optional[float] = None