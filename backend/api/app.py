import os
from time import perf_counter

from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.responses import PlainTextResponse

from backend.api.models import (
    TaskRequest,
    TaskResponse,
    VoiceSTTRequest,
    VoiceTTSRequest,
    VoiceWakeWordRequest,
)
from backend.core.controller import ECFController
from backend.core.observability.logging import metrics_collector
from backend.tools.voice import VoiceSTTTool, VoiceTTSTool, VoiceWakeWordTool

app = FastAPI(title="JARVISv4 API", version="0.1.0")
router = APIRouter()


@router.get("/metrics", response_class=PlainTextResponse)
async def metrics() -> str:
    return metrics_collector.get_prometheus_metrics()


@router.get("/healthz")
async def healthz() -> dict:
    return {"status": "ok"}


@router.post("/v1/tasks", response_model=TaskResponse)
async def create_task(payload: TaskRequest) -> TaskResponse:
    if not payload.goal.strip():
        raise HTTPException(status_code=400, detail="goal must be non-empty")

    start_time = perf_counter()
    success = False
    controller = ECFController()
    try:
        task_id = await controller.run_task(payload.goal)
        error = controller.last_error if controller.state.value == "FAILED" else None
        success = controller.state.value != "FAILED"
    finally:
        elapsed = perf_counter() - start_time
        metrics_collector.increment_requests(
            success=success,
            tokens_used=0,
            execution_time=elapsed
        )

    return TaskResponse(task_id=task_id, state=controller.state.value, error=error)


@router.post("/voice/stt")
async def voice_stt(payload: VoiceSTTRequest) -> dict:
    tool = VoiceSTTTool()
    params = payload.model_dump(exclude_none=True)
    return await tool.execute(**params)


@router.post("/voice/tts")
async def voice_tts(payload: VoiceTTSRequest) -> dict:
    tool = VoiceTTSTool()
    params = payload.model_dump(exclude_none=True)
    return await tool.execute(**params)


@router.post("/voice/wake_word")
async def voice_wake_word(payload: VoiceWakeWordRequest) -> dict:
    tool = VoiceWakeWordTool()
    params = payload.model_dump(exclude_none=True)
    return await tool.execute(**params)


app.include_router(router)
api_prefix = os.getenv("API_PREFIX", "").strip()
if api_prefix:
    if not api_prefix.startswith("/"):
        api_prefix = f"/{api_prefix}"
    app.include_router(router, prefix=api_prefix)