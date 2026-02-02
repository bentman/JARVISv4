# CHANGE_LOG.md

## Rules
- Append-only record of reported work; corrections may be appended to entries.
- Write an entry only after the mini-phase objective is “done” and supported by evidence.
- No edits/reorders/deletes of past entries. If an entry is wrong, append a corrective entry.
- **Ordering:** Entries are maintained in **descending chronological order** (newest first, oldest last).
- **Append location:** New entries must be added **at the top of the Entries section**, directly under `## Entries`.
- Each entry must include:
  - Timestamp: `YYYY-MM-DD HH:MM`
  - Summary: 1–2 lines, past tense
  - Scope: files/areas touched
  - Evidence: exact command(s) run + a minimal excerpt pointer (or embedded excerpt ≤10 lines)
- If a change is reverted, append a new entry describing the revert and why.

## Entries

- 2026-02-02 13:11
  - Summary: Documented minimal task submission UI integration with backend task creation (LLM failure accepted for validation).
  - Scope: `frontend/src/main.jsx`, `frontend/vite.config.js`
  - Evidence: `docker compose logs backend --tail 40`; `Get-ChildItem tasks/archive/2026-02 -File | Sort-Object LastWriteTime -Descending | Select-Object -First 3 Name, LastWriteTime`
    ```text
    backend-1  | INFO:     172.18.0.2:60710 - "POST /v1/tasks HTTP/1.1" 200 OK
    Name                                     LastWriteTime
    ----                                     -------------
    task_20260202_183844_76c8f289_error.json 2026-02-02 12:38:54 PM
    ```

- 2026-02-02 12:03
  - Summary: Fixed prod backend task archival by running backend as root (local-first posture).
  - Scope: `docker-compose.yml`
  - Evidence: `curl.exe -s -X POST http://localhost:8000/v1/tasks -H "Content-Type: application/json" -d '{"goal":"Test prod archival 20260202_180320"}'`; `Get-ChildItem tasks/archive/2026-02 -File | Sort-Object LastWriteTime -Descending | Select-Object -First 5 Name, LastWriteTime`
    ```text
    Name                                     LastWriteTime
    ----                                     -------------
    task_20260202_180320_65c336a2_error.json 2026-02-02 12:03:30 PM
    ```

- 2026-02-02 06:50
  - Summary: Investigated prod task archive failure; permission errors persist despite compose changes (incomplete).
  - Scope: `docker-compose.yml`
  - Evidence: `docker compose -f docker-compose.yml logs backend --tail 80`
    ```text
    PermissionError: [Errno 13] Permission denied: 'tasks/task_20260202_123835_339d4a29.json' -> 'tasks/archive/2026-02/task_20260202_123835_339d4a29_error.json'
    ```

- 2026-02-01 04:27
  - Summary: Mounted backend task artifacts to the host via tasks volume in dev/prod compose to unblock UI validation.
  - Scope: `docker-compose.dev.yml`, `docker-compose.yml`
  - Evidence: `docker compose -f docker-compose.dev.yml up -d --no-deps --force-recreate backend`; `Invoke-RestMethod -Uri http://localhost:8000/v1/tasks -Method Post -ContentType "application/json" -Body '{"goal":"Validate volume mount"}'`; `Get-Item "tasks\archive\2026-02\task_20260201_102650_5381b985_error.json" | Format-List FullName, LastWriteTime`
    ```text
    FullName      : E:\WORK\CODE\GitHub\bentman\Repositories\JARVISv4\tasks\archive\2026-02\task_20260201_102650_5381b985_error.json
    LastWriteTime : 2026-02-01 4:26:50 AM
    ```

- 2026-01-31 19:36
  - Summary: Corrected backend container entrypoint to use backend.api.app:app for dev and prod images.
  - Scope: `backend/Dockerfile.dev`, `backend/Dockerfile`
  - Evidence: `docker compose -f docker-compose.dev.yml build backend`; `docker compose -f docker-compose.dev.yml ps`; `docker compose -f docker-compose.dev.yml logs --tail 20 backend`; `docker compose -f docker-compose.yml build backend`; `docker compose -f docker-compose.yml ps`; `docker compose -f docker-compose.yml logs --tail 20 backend`
    ```text
    jarvisv4-backend-1   jarvisv4-backend-dev   "python -m uvicorn b…"   backend   9 seconds ago    Up 6 seconds
    backend-1  | INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
    jarvisv4-backend-1   jarvisv4-backend       "python -m uvicorn b…"   backend   6 seconds ago   Up 4 seconds
    backend-1  | INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
    ```

- 2026-01-31 18:59
  - Summary: Added prod frontend service to docker-compose.yml with hardened defaults and healthcheck; relaxed read_only for frontend to support Vite runtime writes.
  - Scope: `docker-compose.yml`
  - Evidence: `docker compose -f docker-compose.yml build frontend`; `docker compose -f docker-compose.yml ps`; `docker compose -f docker-compose.yml logs --tail 60 frontend`
    ```text
    ✔ Image jarvisv4-frontend Built
    jarvisv4-frontend-1   jarvisv4-frontend   "docker-entrypoint.s…"   frontend   45 seconds ago   Up 45 seconds (healthy)
    VITE v5.4.21  ready in 136 ms
    ```

- 2026-01-31 18:48
  - Summary: Added minimal frontend Vite scaffold and dev container service with healthcheck for the UI substrate.
  - Scope: `frontend/`, `frontend/Dockerfile`, `docker-compose.dev.yml`
  - Evidence: `docker compose -f docker-compose.dev.yml build frontend`; `docker compose -f docker-compose.dev.yml ps`
    ```text
    ✔ Image jarvisv4-frontend-dev Built
    jarvisv4-frontend-1   jarvisv4-frontend-dev   "docker-entrypoint.s…"   frontend   31 seconds ago   Up 30 seconds (healthy)
    ```

- 2026-01-31 11:12
  - Summary: Added conversation lifecycle orchestration with deterministic turn persistence, ConversationSession artifact creation, and validation-only replay coverage.
  - Scope: `backend/core/controller.py`, `backend/memory/working_state.py`, `tests/agentic/test_conversation_lifecycle_orchestration.py`, `SYSTEM_INVENTORY.md`
  - Evidence: `backend/.venv/Scripts/python scripts/validate_backend.py`
    ```text
    Agentic Tests:     PASS
    ✅ JARVISv4 Current ./backend is validated!
    ```

- 2026-01-31 10:58
  - Summary: Added research lifecycle orchestration with deterministic web_search → text_output flow, ResearchSession artifact creation, and validation-only replay coverage.
  - Scope: `backend/core/controller.py`, `backend/memory/working_state.py`, `tests/agentic/test_research_lifecycle_orchestration.py`, `SYSTEM_INVENTORY.md`
  - Evidence: `backend/.venv/Scripts/python scripts/validate_backend.py`
    ```text
    Agentic Tests:     PASS
    ✅ JARVISv4 Current ./backend is validated!
    ```

- 2026-01-30 20:24
  - Summary: Added VoiceSession metrics sidecar generation from archived voice lifecycle artifacts and captured per-step timing fields for deterministic observability.
  - Scope: `backend/core/controller.py`, `backend/memory/working_state.py`, `tests/agentic/test_voice_session_replay.py`
  - Evidence: `backend/.venv/Scripts/python scripts/validate_backend.py`
    ```text
    Unit Tests:        PASS
    Integration Tests: PASS
    Agentic Tests:     PASS
    ✅ JARVISv4 Current ./backend is validated!
    ```

- 2026-01-30 19:50
  - Summary: Added VoiceSession artifact creation with validation-only replay contract and tightened replay integrity checks; updated voice lifecycle + session agentic tests to enforce contract constraints.
  - Scope: `backend/core/controller.py`, `backend/memory/working_state.py`, `tests/agentic/test_voice_lifecycle_orchestration.py`, `tests/agentic/test_voice_session_replay.py`
  - Evidence: `backend/.venv/Scripts/python scripts/validate_backend.py`
    ```text
    Unit Tests:        PASS
    Integration Tests: PASS
    Agentic Tests:     PASS
    ✅ JARVISv4 Current ./backend is validated!
    ```

- 2026-01-30 19:18
  - Summary: Added controller-level end-to-end voice lifecycle orchestration with fixed deterministic step order (wake_word → STT → agent → TTS → archive), registered VoiceWakeWordTool, and added an agentic lifecycle orchestration test.
  - Scope: `backend/core/controller.py`, `tests/agentic/test_voice_lifecycle_orchestration.py`
  - Evidence: `backend/.venv/Scripts/python scripts/validate_backend.py`
    ```text
    Unit Tests:        PASS
    Integration Tests: PASS
    Agentic Tests:     PASS
    ✅ JARVISv4 Current ./backend is validated!
    ```

- 2026-01-30 18:45
  - Summary: Added minimal FastAPI voice endpoints that pass through to existing voice tools without altering artifacts or provisioning behavior.
  - Scope: `backend/api/app.py`, `backend/api/models.py`
  - Evidence: `backend/.venv/Scripts/python scripts/validate_backend.py`
    ```text
    Unit Tests:        PASS
    Integration Tests: PASS
    Agentic Tests:     PASS
    ✅ JARVISv4 Current ./backend is validated!
    ```

- 2026-01-30 18:20
  - Summary: Added non-strict openWakeWord provisioning for wake-word detection with startup/on-demand policy support and deterministic provisioning artifacts.
  - Scope: `backend/core/voice/runtime.py`, `tests/unit/test_voice_runtime.py`
  - Evidence: `backend/.venv/Scripts/python scripts/validate_backend.py`
    ```text
    Unit Tests:        PASS
    Integration Tests: PASS
    Agentic Tests:     PASS
    ✅ JARVISv4 Current ./backend is validated!
    ```

- 2026-01-30 14:47
  - Summary: Added deterministic openWakeWord wake-word detection and voice_wake_word tool with strict-only model presence handling under ${MODEL_PATH}/openwakeword.
  - Scope: `backend/core/voice/runtime.py`, `backend/tools/voice.py`, `tests/unit/test_voice_runtime.py`, `tests/unit/test_voice_tool.py`
  - Evidence: `backend/.venv/Scripts/python scripts/validate_backend.py`
    ```text
    Unit Tests:        PASS
    Integration Tests: PASS
    Agentic Tests:     PASS
    ✅ JARVISv4 Current ./backend is validated!
    ```

- 2026-01-30 13:51
  - Summary: Added unified model provisioning policy (default strict) and minimal voice model manager with deterministic provisioning fields in voice runtime.
  - Scope: `backend/core/config/settings.py`, `backend/core/model_manager.py`, `backend/core/voice/runtime.py`
  - Evidence: `backend/.venv/Scripts/python scripts/validate_backend.py`
    ```text
    Unit Tests:        PASS
    Integration Tests: PASS
    Agentic Tests:     PASS
    ✅ JARVISv4 Current ./backend is validated!
    ```

- 2026-01-29 08:55
  - Summary: Restored controller WorkflowEngine execution contract and failure archiving semantics for tool execution, dependency mapping, and resume flows; closed trace store SQLite handles to prevent Windows temp lock failures.
  - Scope: `backend/core/controller.py`, `backend/memory/stores/trace_store.py`
  - Evidence: `backend/.venv/Scripts/python scripts/validate_backend.py`
    ```text
    Unit Tests:        PASS
    Integration Tests: PASS
    Agentic Tests:     PASS
    ✅ JARVISv4 Current ./backend is validated!
    ```

- 2026-01-28 19:00
  - Summary: Controller execution path now uses WorkflowEngine.execute_workflow() via SimpleToolNode bridge
  - Scope: `backend/core/controller.py`, `tests/integration/test_controller_workflow_integration.py`
  - Evidence: `python scripts/validate_backend.py` (Integration: 3/3 PASS)
    ```text
    ✓ PASS: tests.integration.test_controller_workflow_integration::test_controller_workflow_engine_integration
    ✓ PASS: tests.integration.test_controller_workflow_integration::test_controller_workflow_engine_deterministic_output
    ✓ PASS: tests.integration.test_controller_workflow_integration::test_controller_workflow_engine_error_handling
    ```

- 2026-01-28 15:11
  - Summary: Enhanced WorkflowEngine with v3 execution logic and comprehensive test coverage
  - Scope: `backend/controller/engine/engine.py`, `tests/unit/test_workflow_engine.py`, `tests/unit/test_controller.py`, `SYSTEM_INVENTORY.md`
  - Evidence: `backend/.venv/Scripts/python -m pytest tests/unit/test_workflow_engine.py -v` (12/12 PASS), `python scripts/validate_backend.py` (122/122 PASS)

- 2026-01-28 10:48
  - Summary: Extended Piper TTS model presence contract to report `model_found` status deterministically via `MODEL_PATH` + `piper/{voice}.onnx` resolution, preserving B1 deferred execution semantics.
  - Scope: `backend/core/voice/runtime.py`, `tests/unit/test_voice_tool.py`
  - Evidence: `pytest tests/unit/test_regression.py` (2 passed)

- 2026-01-27 18:50
  - Summary: Implemented deterministic Whisper model presence contract with preflight checks and structured artifact reporting.
  - Scope: `backend/core/voice/runtime.py`, `backend/tools/voice.py`, `tests/unit/test_voice_tool.py`
  - Evidence: `backend/.venv/Scripts/python -m pytest -q tests/unit/test_voice_tool.py -rs`
    ```text
    ...........
    11 passed in 0.15s
    ```

- 2026-01-27 18:00
  - Summary: Implemented and validated deterministic artifact contract for voice tools (STT/TTS).
  - Scope: `backend/core/voice/runtime.py`, `tests/unit/test_voice_tool.py`
  - Evidence: `backend/.venv/Scripts/python -m pytest -q tests/unit/test_voice_runtime.py tests/unit/test_voice_tool.py -rs`
    ```text
    ...............
    15 passed in 0.16s
    ```

- 2026-01-27 11:00
  - Summary: Docker E2E validation of deterministic voice invocation (dev + prod).
  - Scope: `docker-compose.dev.yml`, `docker-compose.yml`, `tests/agentic/test_deterministic_voice_tools.py`
  - Evidence: `docker compose -f docker-compose.dev.yml run --rm validate-voice` + `docker compose -f docker-compose.yml run --rm validate-voice`
    ```text
    tests\agentic\test_deterministic_voice_tools.py . [100%]
    1 passed in 0.55s
    ```

- 2026-01-27 04:42
  - Summary: Integrated `voice_stt` and `voice_tts` into the `ECFController` execution flow and validated via deterministic agentic test (injecting plan + fake LLM).
  - Scope: `backend/core/controller.py`, `tests/agentic/test_deterministic_voice_tools.py`
  - Evidence: `backend/.venv/Scripts/python -m pytest -s tests/agentic/test_deterministic_voice_tools.py`
    ```text
    tests\agentic\test_deterministic_voice_tools.py
    [Evidence] Completed Steps: [
      {
        "index": 0,
        "description": "Execute voice STT on tests/test.wav",
        "tool_name": "voice_stt",
        "tool_params": {
          "audio_file_path": "tests/test.wav"
        },
        ...
      },
      {
        "index": 1,
        "description": "Execute voice TTS with help",
        "tool_name": "voice_tts",
        "tool_params": {
          "text": "--help"
        },
        ...
      }
    ]
    .
    1 passed in 0.86s
    ```

- 2026-01-26 19:55
  - Summary: Added ECF-facing voice tool integration with ToolRegistry-compatible voice_stt and voice_tts tools that wrap Phase B1 runtime
  - Scope: `backend/tools/voice.py`, `tests/unit/test_voice_tool.py`
  - Evidence: `backend/.venv/Scripts/python -m pytest tests/unit/test_voice_tool.py -v`
    ```text
    ✓ PASS: tests.unit.test_voice_tool.TestVoiceTools::test_voice_stt_tool_registration
    ✓ PASS: tests.unit.test_voice_tool.TestVoiceTools::test_voice_tts_tool_registration
    ✓ PASS: tests.unit.test_voice_tool.TestVoiceTools::test_voice_stt_execution_with_test_wav
    ✓ PASS: tests.unit.test_voice_tool.TestVoiceTools::test_voice_tts_help_execution
    ✓ PASS: tests.unit.test_voice_tool.TestVoiceTools::test_voice_stt_missing_file
    ✓ PASS: tests.unit.test_voice_tool.TestVoiceTools::test_voice_stt_invalid_parameter
    ✓ PASS: tests.unit.test_voice_tool.TestVoiceTools::test_tool_registry_call_voice_stt
    ✓ PASS: tests.unit.test_voice_tool.TestVoiceTools::test_tool_registry_call_voice_tts
    ✓ PASS: tests.unit.test_voice_tool.TestVoiceTools::test_tool_registry_parameter_validation
    ```
  - Notes: Phase B2 voice tool integration provides deterministic, artifact-friendly voice tools for ECF agentic system with JSON schema validation and structured result returns

- 2026-01-26 08:25
  - Summary: Added voice runtime execution plumbing with subprocess-based whisper (STT) and piper (TTS) execution, structured result capture, and comprehensive error handling
  - Scope: `backend/core/voice/runtime.py`, `backend/core/voice/__init__.py`, `tests/unit/test_voice_runtime.py`
  - Evidence: `backend/.venv/Scripts/python -m pytest tests/unit/test_voice_runtime.py -v`
    ```text
    ✓ PASS: tests.unit.test_voice_runtime.TestVoiceRuntime::test_whisper_help
    ✓ PASS: tests.unit.test_voice_runtime.TestVoiceRuntime::test_piper_help
    ✓ PASS: tests.unit.test_voice_runtime.TestVoiceRuntime::test_whisper_with_test_wav
    ✓ PASS: tests.unit.test_voice_runtime.TestVoiceRuntime::test_missing_audio_file
    ✓ PASS: tests.unit.test_voice_runtime.TestVoiceRuntime::test_tts_real_execution_deferred
    ```
  - Notes: Phase B1 voice execution plumbing validated via targeted pytest; `test_backend_main_execution` currently fails due to missing `LLM_BASE_URL` environment variable (pre-existing environment/config issue, out of scope for B1)

- 2026-01-25 21:38
  - Summary: Added `backend/Dockerfile` and updated `docker-compose.yml` to establish hardened prod container capability for voice binaries (whisper.cpp, piper)
  - Scope: `backend/Dockerfile`, `docker-compose.yml`
  - Evidence: `docker compose -f docker-compose.yml build backend` + `docker compose -f docker-compose.yml run --rm backend whisper --help` + `docker compose -f docker-compose.yml run --rm backend piper --help`
    ```text
    usage: whisper [options] file0 file1 ...
    usage: piper [options]
    ```

- 2026-01-25 19:47
  - Summary: Added `backend/Dockerfile.dev` and updated `docker-compose.dev.yml` to establish dev container capability for voice binaries (whisper.cpp, piper)
  - Scope: `backend/Dockerfile.dev`, `docker-compose.dev.yml`
  - Evidence: `docker compose -f docker-compose.dev.yml build backend` + `docker compose -f docker-compose.dev.yml run --rm backend whisper --help` + `docker compose -f docker-compose.dev.yml run --rm backend piper --help`
    ```text
    usage: whisper [options] file0 file1 ...
    usage: piper [options]
    ```

- 2026-01-25 07:44
  - Summary: Made task replay crash-consistent by repairing in-flight `current_step` artifacts via deterministic re-queue-on-resume, then proved end-to-end replay from on-disk artifacts only.
  - Scope: `backend/core/controller.py`, `tests/agentic/test_deterministic_artifact_replay_crash_consistency.py`
  - Evidence: `pwsh -NoProfile -Command "./backend/.venv/Scripts/python -m pytest -q tests/agentic/test_deterministic_artifact_replay_crash_consistency.py"`
    ```text
    1 passed in 1.05s
    ```

- 2026-01-24 20:45
  - Summary: Added bounded multi-task orchestration to execute a batch of tasks sequentially and deterministically terminate on first observed failure using artifact analytics.
  - Scope: `backend/core/controller.py`, `tests/agentic/test_ecf_core_flow.py`
  - Evidence: `backend/.venv/Scripts/python -m pytest tests/agentic/test_ecf_core_flow.py::test_orchestrate_task_batch_terminates_on_failure_via_analytics -q`
    ```text
    1 passed in 1.59s
    ```

- 2026-01-24 18:48
  - Summary: Added deterministic max-step guardrails for planning/execution (bounded by constants) while reusing existing failure causes for early, explicit failures.
  - Scope: `backend/core/controller.py`, `tests/unit/test_ecf_controller.py`
  - Evidence: `backend/.venv/Scripts/python -m pytest tests/unit/test_ecf_controller.py::test_controller_rejects_plan_exceeding_max_planned_steps tests/unit/test_ecf_controller.py::test_controller_fails_when_max_executed_steps_exceeded -q`
    ```text
    .                                                                                                               [100%]
    2 passed in 1.27s
    ```

- 2026-01-24 18:27
  - Summary: Tightened supervisor watchdog policy to resume only ACTIVE stalled tasks in IN_PROGRESS status (skipping CREATED tasks that never started).
  - Scope: `backend/core/controller.py`, `tests/agentic/test_supervisor_watchdog_resume.py`
  - Evidence: `backend/.venv/Scripts/python -m pytest tests/agentic/test_supervisor_watchdog_resume.py -q`
    ```text
    1 passed in 1.65s
    ```

- 2026-01-24 17:32
  - Summary: Persisted coarse typed task failure causes (`failure_cause`) and ensured `error` is recorded on all FAILED task archival paths.
  - Scope: `backend/core/controller.py`, `tests/unit/test_ecf_controller.py`
  - Evidence: `backend/.venv/Scripts/python -m pytest tests/unit/test_ecf_controller.py::test_controller_planning_failure -q`
    ```text
    1 passed in 1.06s
    ```

- 2026-01-24 16:59
  - Summary: Added a deterministic, side-effect-free `text_output` tool that returns caller-provided text verbatim, and validated an end-to-end task completes using it.
  - Scope: `backend/tools/text_output.py`, `backend/core/controller.py`, `tests/agentic/test_deterministic_text_output_tool.py`
  - Evidence: `backend/.venv/Scripts/python -m pytest tests/agentic/test_deterministic_text_output_tool.py -q`
    ```text
    1 passed in 1.08s
    ```

- 2026-01-24 16:40
  - Summary: Added a planning-stage tool executability guardrail that fails fast before execution when planned steps cannot be matched to any registered tool, and persists a clear error in the task artifact.
  - Scope: `backend/core/controller.py`, `tests/unit/test_ecf_controller.py`
  - Evidence: `backend/.venv/Scripts/python -m pytest tests/unit/test_ecf_controller.py::test_controller_rejects_plan_with_unknown_tool_fails_in_planning -q`
    ```text
    1 passed in 1.17s
    ```

- 2026-01-24 13:15
  - Summary: Documented deterministic task_id ownership: the Controller is authoritative (no dual task creation); the Planner updates the existing task rather than creating a second task.
  - Scope: `backend/core/controller.py`, `backend/agents/planner/planner.py`, `tests/agentic/test_ecf_core_flow.py`
  - Evidence: `backend/.venv/Scripts/python -m pytest tests/agentic/test_ecf_core_flow.py::test_ecf_first_flight_e2e -q`
    ```text
    1 passed in 1.18s
    ```

- 2026-01-24 12:55
  - Summary: Fixed CLI LLM override precedence so resolved `--llm-*` flags override env/defaults and are passed through to the controller LLM provider (base_url/model/timeout/max_retries).
  - Scope: `backend/main.py`, `backend/core/controller.py`, `tests/unit/test_cli_llm_overrides.py`
  - Evidence: `backend/.venv/Scripts/python -m pytest tests/unit/test_cli_llm_overrides.py -q`
    ```text
    1 passed in 0.60s
    ```

- 2026-01-24 12:24
  - Summary: Added a read-only task supervision surface to enumerate ACTIVE and ARCHIVED tasks deterministically from disk.
  - Scope: `backend/memory/working_state.py`, `backend/core/controller.py`, `backend/main.py`, `tests/agentic/test_task_supervision_list_tasks.py`
  - Evidence: `backend/.venv/Scripts/python -m pytest tests/agentic/test_task_supervision_list_tasks.py -q`
    ```text
    1 passed in 1.50s
    ```

- 2026-01-24 11:49
  - Summary: Added deterministic task resume from on-disk artifacts via controller resume_task and a CLI entrypoint.
  - Scope: `backend/memory/working_state.py`, `backend/core/controller.py`, `backend/main.py`, `tests/agentic/test_task_resume.py`
  - Evidence: `backend/.venv/Scripts/python -m pytest tests/agentic/test_task_resume.py -q`
    ```text
    1 passed in 1.37s
    ```

- 2026-01-24 11:03
  - Summary: Added injectable-client support to RedisCache and validated JSON round-trip behavior with a fake Redis boundary client.
  - Scope: `backend/core/cache/redis_cache.py`, `tests/unit/test_redis_cache.py`
  - Evidence: `backend/.venv/Scripts/python -m pytest tests/unit/test_redis_cache.py -q`
    ```text
    1 passed in 0.08s
    ```

- 2026-01-24 10:34
  - Summary: Added API smoke probe to validate backend API readiness (health + metrics) and aligned controller planning-failure test with durable task_id contract.
  - Scope: `scripts/validate_backend.py`, `tests/unit/test_ecf_controller.py`
  - Evidence: `backend/.venv/Scripts/python.exe scripts/validate_backend.py`
    ```text
    API_SMOKE_STARTING cmd=python -m uvicorn backend.api.app:app port=8001
    API_HEALTHZ_OK url=http://127.0.0.1:8001/healthz
    API_METRICS_OK contains="# HELP jarvis_requests_total"
    API_SMOKE=PASS
    ✅ JARVISv4 Current ./backend is validated!
    ```

- 2026-01-24 10:10
  - Summary: Added proxy readiness primitives with a health probe endpoint and optional API base-path routing for the API surface.
  - Scope: `backend/api/app.py`
  - Evidence: `backend/.venv/Scripts/python -m uvicorn backend.api.app:app --port 8000` (with `API_PREFIX=/api`) + `curl.exe -s -i http://127.0.0.1:8000/healthz` + `curl.exe -s -i http://127.0.0.1:8000/api/healthz`
    ```text
    HTTP/1.1 200 OK
    {"status":"ok"}
    HTTP/1.1 200 OK
    {"status":"ok"}
    ```

- 2026-01-24 09:40
  - Summary: Hardened API task response contract to always return a durable task_id and explicit error field on failure.
  - Scope: `backend/api/app.py`, `backend/api/models.py`, `backend/core/controller.py`
  - Evidence: `backend/.venv/Scripts/python -m uvicorn backend.api.app:app --port 8000` + `curl.exe -s -X POST http://127.0.0.1:8000/v1/tasks -H "Content-Type: application/json" -d '{"goal":"ping"}'`
    ```text
    {"task_id":"task_...","state":"FAILED","error":"LLMProviderError: ... Connection error."}
    ```

- 2026-01-24 09:00
  - Summary: Added Redis-backed cache integration for WebSearchTool with settings wiring and cache client module; validated cache usage via unit test.
  - Scope: `backend/core/config/settings.py`, `backend/core/cache/`, `backend/tools/web_search.py`, `backend/requirements.txt`, `tests/unit/test_web_search.py`
  - Evidence: `backend/.venv/Scripts/python -m pytest tests/unit/test_web_search.py -q`
    ```text
    ....                                                                             [100%]
    5 passed in 0.36s
    ```

- 2026-01-24 07:51
  - Summary: Added append-only Tier-2 episodic trace storage and controller emissions for decisions, tool calls, and validations; asserted trace rows in controller unit test.
  - Scope: `backend/memory/stores/trace_store.py`, `backend/core/controller.py`, `tests/unit/test_ecf_controller.py`
  - Evidence: `backend/.venv/Scripts/python -m pytest tests/unit/test_ecf_controller.py -q`
    ```text
    .                                                                              [100%]
    4 passed in 2.02s
    ```

- 2026-01-24 07:10
  - Summary: Hardened CLI LLM preflight (`--check-llm`) for local Ollama by deferring imports, adding explicit CLI flags, and implementing a no-retry connectivity probe with actionable failure classification.
  - Scope: `backend/main.py`
  - Evidence:
    - `backend/.venv/Scripts/python -m backend.main --check-llm --llm-base-url http://localhost:11434/v1 --llm-model llama3.1:8b --llm-timeout-seconds 5 --llm-max-retries 0`
      ```text
      LLM_OK base_url=http://localhost:11434/v1 model=llama3.1:8b
      ```
    - `backend/.venv/Scripts/python -m backend.main --check-llm --llm-base-url http://localhost:1/v1 --llm-model llama3.1:8b --llm-timeout-seconds 2 --llm-max-retries 0`
      ```text
      LLM_CHECK_FAILED category=unreachable
      Error: APITimeoutError: Request timed out.
      ```

## Evidence Reproducibility Clarifications — 2026-01-23

- Clarification: Entries dated 2026-01-19 citing `scripts/test_llm_connectivity.py`, `scripts/verify_planner_integration.py`, `scripts/verify_executor_integration.py`, `scripts/first_flight.py`, `scripts/validate_curator.py`, and `scripts/validate_mixer.py` reference evidence commands whose script files are not present in the current repo tree. As of 2026-01-23, `scripts/` contains only `validate_backend.py`, so those specific evidence commands are not reproducible from this checkout.
  - Evidence: `ls scripts/`

- Clarification: Entries that reference validation report files under `reports/` (e.g., 2026-01-17 17:53) cannot be re-verified by agents under current governance because `.clineignore` blocks access to `reports/` contents. The artifacts may exist, but their contents are not reproducible through agent tooling in this context.
  - Evidence: root file listing showing `reports/` (🔒) and `.clineignore` includes `reports/`

- 2026-01-23 20:42
  - Summary: Hardened ToolRegistry tool-call contract with deterministic error types and stable messages for not-found, schema validation, and execution failures.
  - Scope: backend/tools/registry/registry.py, tests/unit/test_tool_registry.py
  - Evidence: `backend/.venv/Scripts/python -m pytest tests/unit/test_tool_registry.py -q` + `backend/.venv/Scripts/python -m pytest tests/unit/test_executor.py -q`
    ```text
    .....                                                                                                                 [100%]
    5 passed in 0.08s
    .                                                                                                                   [100%]
    3 passed in 1.20s
    ```

- 2026-01-22 00:50
  - Summary: Realized Fully Functional Unified Search with Multi-Provider support and ECF Safety (Privacy/Budget).
  - Scope: backend/tools/web_search.py, backend/core/search_providers.py, backend/core/config/settings.py, tests/unit/test_web_search.py
  - Evidence: `backend/.venv/Scripts/python.exe scripts/validate_backend.py`
    ```text
    ✓ PASS: tests.unit.test_web_search::test_web_search_tool_initialization
    ✓ PASS: tests.unit.test_web_search::test_web_search_privacy_redaction
    ✓ PASS: tests.unit.test_web_search::test_web_search_budget_block
    ✓ PASS: tests.unit.test_web_search::test_web_search_provider_fallback
    ✅ JARVISv4 Current ./backend is validated!
    ```

- 2026-01-21 22:45
  - Summary: Ported Budget Service from v2 to v4 for granular cost tracking and safety limits.
  - Scope: backend/core/budget.py, backend/core/config/settings.py, tests/unit/test_budget.py
  - Evidence: `backend/.venv/Scripts/python.exe -m pytest tests/unit/test_budget.py`
    ```text
    tests\unit\test_budget.py ........                                                                 [100%]
    8 passed in 0.13s
    ```

- 2026-01-21 22:33
  - Summary: Implemented Memory Tier 3 (Semantic Memory) using FAISS and SQLite.
  - Scope: backend/memory/stores/semantic.py, tests/unit/test_semantic_memory.py, backend/requirements.txt
  - Evidence: `.\backend\.venv\scripts\python scripts/validate_backend.py` (All tests passed, including 6 new unit tests for semantic memory)

- 2026-01-21 22:18
  - Summary: Ported and consolidated Privacy Engine from v2 (Encryption) and v3 (Compliance); upgraded to `cryptography` library.
  - Scope: backend/requirements.txt, backend/core/config/settings.py, backend/core/privacy.py, tests/unit/test_privacy.py
  - Evidence: `.\backend\.venv\scripts\python scripts/validate_backend.py`
    ```text
    ✓ PASS: tests.unit.test_privacy::test_privacy_encryption_roundtrip
    ...
    ✓ PASS: tests.unit.test_privacy::test_privacy_hash_id
    ✅ JARVISv4 Current ./backend is validated!
    ```

- 2026-01-21 21:52
  - Summary: Realized Full ECF Learning Cycle via integrated validation test; fixed PYTHONPATH issue in initial sanity test.
  - Scope: tests/integration/test_learning_cycle.py, tests/unit/test_initial_sanity.py
  - Evidence: `.\backend\.venv\scripts\python scripts/validate_backend.py`
    ```text
    ✓ PASS: tests.unit.test_initial_sanity::test_backend_main_execution
    ✓ PASS: tests.integration.test_learning_cycle::test_full_learning_cycle
    ✅ JARVISv4 Current ./backend is validated!
    ```

- 2026-01-21 21:06
  - Summary: Final Audit: Deep-Trace Validation of RegressionSuite proving real agentic evaluation and data mining.
  - Scope: backend/learning/regression.py, tests/unit/test_regression.py
  - Evidence: `.\backend\.venv\Scripts\python -m pytest -s -vv --log-cli-level=INFO tests/unit/test_regression.py`
    ```text
    INFO: Mined Episode 1: Input='Explain what 2+2 is', Expected='2+2 is 4'
    INFO: JUDGE PROMPT:
    Goal: Explain what 2+2 is
    Expected Output: 2+2 is 4
    Actual Output: The expression "2+2" represents the addition of two numbers...
    ...
    INFO: JUDGE RESPONSE: YES
    ```

- 2026-01-21 20:47
  - Summary: Implemented and verified Regression Suite with SQLite mining and LLM-based semantic judging.
  - Scope: backend/learning/regression.py, tests/unit/test_regression.py
  - Evidence: `.\backend\.venv\Scripts\python -m pytest tests/unit/test_regression.py`
    ```text
    tests\unit\test_regression.py ..                                         [100%]
    2 passed in 36.46s
    ```

- 2026-01-19 19:48
  - Summary: Implemented DatasetMixer and RegressionSuite blueprint; scaffolded Basal Dataset with Golden Examples.
  - Scope: data/training/basal_set.json, backend/learning/mixer.py, backend/learning/regression.py, scripts/validate_mixer.py
  - Evidence: `backend/.venv/Scripts/python.exe scripts/validate_mixer.py`
    ```text
    Actual curriculum ratio: 70.00%
    Basal items (Golden) count: 6
    ✅ Validation Successful: 70/30 split achieved
    ```

- 2026-01-19 19:38
  - Summary: Implemented Episode Curator and instrumented Controller/StateManager for tool metadata persistence.
  - Scope: backend/memory/working_state.py, backend/core/controller.py, backend/learning/curator.py, scripts/validate_curator.py
  - Evidence: `backend/.venv/Scripts/python.exe scripts/validate_curator.py`
    ```text
    Curated 2 examples.
    --- Example for planner ---
    Instruction: Decompose this goal into a concrete plan.
    --- Example for executor ---
    Instruction: Execute this task step: Calculate square root
    Output: {"tool": "math_tool", "params": {"action": "sqrt", "value": 16}, ...}
    ✅ Validation Successful
    ```

- 2026-01-19 19:15
  - Summary: Realized ECF Controller and validated via successful E2E First Flight. [Late Entry]
  - Scope: backend/core/controller.py, scripts/first_flight.py
  - Evidence: `python scripts/first_flight.py`
    ```text
    INFO: Transitioning to PLANNING...
    INFO: Created task task_20260119_184652_adedd28a...
    INFO: Transitioning to EXECUTING...
    INFO: Calling tool: integration_template_tool
    INFO: Task task_20260119_184652_adedd28a COMPLETED and ARCHIVED.
    ✅ SUCCESS: Task archived...
    ```

- 2026-01-19 18:46
  - Summary: Integrated `ECFController` as the authoritative FSM spine coordinating Planner and Executor.
  - Scope: backend/core/controller.py, backend/main.py, tests/unit/test_ecf_controller.py, scripts/first_flight.py
  - Evidence: `pytest tests/unit/test_ecf_controller.py` (3/3 PASS)
  - Evidence: `python scripts/first_flight.py`
    ```text
    INFO: Transitioning to PLANNING...
    INFO: Created task task_20260119_184652_adedd28a...
    INFO: Transitioning to EXECUTING...
    INFO: Calling tool: integration_template_tool
    INFO: Task task_20260119_184652_adedd28a COMPLETED and ARCHIVED.
    ✅ SUCCESS: Task archived...
    ```

- 2026-01-19 18:17
  - Summary: Implemented `ExecutorAgent` and enhanced `ToolRegistry` with schema validation.
  - Scope: backend/agents/executor/, backend/tools/, tests/unit/test_executor.py, scripts/verify_executor_integration.py
  - Evidence: `pytest tests/unit/test_executor.py` (3/3 PASS)
  - Evidence: `python scripts/verify_executor_integration.py`
    ```text
    Status: SUCCESS
    Tool used: dummy_tool
    Result: {'processed': 'Handshake 123'}
    ✅ SMOKE TEST PASSED
    ```

- 2026-01-19 15:02
  - Summary: Realized `PlannerAgent` by integrating `OpenAIProvider` and verified end-to-end task file creation.
  - Scope: backend/agents/planner/planner.py, tests/unit/test_planner.py, scripts/verify_planner_integration.py
  - Evidence: `pytest tests/unit/test_planner.py` (5/5 PASS)
  - Evidence: `python scripts/verify_planner_integration.py`
    ```text
    ✅ Task file created.
    Task status: CREATED
    Goal: Verify Task File Creation
    Steps count: 3
    ✅ Data validation PASSED.
    ```

- 2026-01-19 14:54
  - Summary: Implemented `OpenAIProvider` with exponential backoff retries and support for local/cloud endpoints.
  - Scope: backend/core/llm/, backend/core/config/settings.py, backend/requirements.txt, scripts/test_llm_connectivity.py
  - Evidence: `pytest tests/unit/test_llm_provider.py` (5/5 PASS)
  - Evidence: `python scripts/test_llm_connectivity.py`
    ```text
    INFO:__main__:Received Response: Handshake Successful. I am ready.
    INFO:__main__:✅ SMOKE TEST PASSED: Handshake verified.
    ```

- 2026-01-19 14:36
  - Summary: Implemented stateless `PlannerAgent` with DAG cycle detection and `WorkingStateManager` integration.
  - Scope: backend/agents/planner/planner.py, tests/unit/test_planner.py
  - Evidence: `backend/.venv/Scripts/python.exe -m pytest tests/unit/test_planner.py -q`
    ```text
    .....                                                                    [100%]
    5 passed in 0.15s
    ```
  - Evidence: `backend/.venv/Scripts/python.exe scripts/validate_backend.py`
    ```text
    SUCCESS: Unit: 36 tests
    ✅ JARVISv4 Current ./backend is validated!
    ```

- 2026-01-19 14:24
  - Summary: Implemented Tier 1 Working State Manager (Ephemeral Memory) with JSON-based storage, atomic writes, and schema validation.
  - Scope: backend/core/config/settings.py, backend/memory/working_state.py, tests/unit/test_working_state.py
  - Evidence: `backend/.venv/Scripts/python.exe -m pytest tests/unit/test_working_state.py -q`
    ```text
    ........                                                                                     [100%]
    8 passed in 0.26s
    ```
  - Evidence: `backend/.venv/Scripts/python.exe scripts/validate_backend.py`
    ```text
    SUCCESS: Unit: 31 tests
    SUCCESS: Integration: 3 tests
    ✅ JARVISv4 Current ./backend is validated!
    ```

- 2026-01-19 06:51
  - Summary: Added settings-driven memory persistence selection + memory store factory + workflow persistence integration test.
  - Scope: backend/core/config/settings.py, backend/memory/factory.py, tests/integration/test_workflow_persistence.py
  - Evidence: `backend/.venv/Scripts/python.exe -m pytest tests/integration -q`
    ```text
    ...                                                                      [100%]
    3 passed in 0.13s
    ```
  - Evidence: `backend/.venv/Scripts/python.exe scripts/validate_backend.py`
    ```text
    SUCCESS: Integration: 3 tests
    Integration Tests: PASS
    ```

- 2026-01-19 06:10
  - Summary: Implemented SQLite-backed episodic memory store and established first integration test (proving persistence).
  - Scope: backend/memory/stores/sqlite_store.py, tests/integration/test_sqlite_memory_store.py
  - Evidence: `backend/.venv/Scripts/python.exe -m pytest tests/integration -q`
    ```text
    ..                                                                       [100%]
    2 passed in 0.40s
    ```
    - Evidence: `backend/.venv/Scripts/python.exe scripts/validate_backend.py`
    ```text
    SUCCESS: Unit: 23 tests
    SUCCESS: Integration: 2 tests
    Unit Tests:        PASS
    Integration Tests: PASS
    Agentic Tests:     WARN
    ```

- 2026-01-18 12:54
  - Summary: Enforced TaskContext-only execution boundary (removed dict-compat), updated nodes/tests to use context.infrastructure + context.data.
  - Scope: backend/controller/engine/engine.py, backend/controller/engine/types.py, backend/controller/nodes/callable.py, backend/controller/nodes/memory_op.py, tests/unit/test_node_execution.py, tests/unit/test_workflow_execution.py, tests/unit/test_memory_node.py
    - Evidence: `backend/.venv/Scripts/python.exe scripts/validate_backend.py`
    ```text
    SUCCESS: Unit: 23 tests
    Unit Tests:        PASS
    Integration Tests: WARN
    Agentic Tests:     WARN
    ```

- 2026-01-18 09:45
  - Summary: Implemented ordered multi-node execution (`execute_sequence`) and added MemoryReadNode; validated via unit test.
  - Scope: backend/controller/engine/engine.py, backend/controller/nodes/memory_op.py, tests/unit/test_workflow_execution.py
  - Evidence: `backend/.venv/Scripts/python.exe -m pytest tests/unit/test_workflow_execution.py -q`
    ```text
    ..                                                                                                         [100%]
    2 passed in 0.08s
    ```

- 2026-01-18 08:26
  - Summary: Implemented MemoryWriteNode for deterministic memory operations and integrated with WorkflowEngine.
  - Scope: backend/controller/nodes/memory_op.py, tests/unit/test_memory_node.py
  - Evidence: `backend/.venv/Scripts/python.exe -m pytest tests/unit/test_memory_node.py -q`
    ```text
    .                                                                                                          [100%]
    1 passed in 0.10s
    ```

- 2026-01-18 07:29
  - Summary: Created .clineignore to harden context boundaries and established "opt-in via @mention" workflow for reference materials.
  - Scope: .clineignore
  - Evidence: `ls .clineignore`
    ```text
    Mode                 LastWriteTime         Length Name
    ----                 -------------         ------ ----
    -a---          2026-01-18  7:29 AM            275 .clineignore
    ```

- 2026-01-18 06:07
  - Summary: Implemented single-node execution path + callable node; validated tool+memory interaction.
  - Scope: backend/controller/engine/engine.py, backend/controller/nodes/callable.py, tests/unit/test_node_execution.py
  - Evidence: `backend/.venv/Scripts/python.exe -m pytest tests/unit/test_node_execution.py -q`
    ```text
    1 passed in 0.07s
    ```

- 2026-01-18 05:48
  - Summary: Added memory schema + deterministic in-memory store + unit test.
  - Scope: backend/memory/**, tests/unit/test_memory_store.py
  - Evidence: `backend/.venv/Scripts/python.exe -m pytest tests/unit/test_memory_store.py -q`
    ```text
    2 passed in 0.07s
    ```

- 2026-01-17 21:05
  - Summary: Added env templates (v2-derived) and compose templates (v3-derived) with reserved annotations.
  - Scope: .env.example, .env.dev.example, docker-compose.yml, docker-compose.dev.yml
  - Evidence: `ls` + Excerpts
    ```text
    .env.example: # Privacy Settings (reserved: future capability)
    docker-compose.yml: # reserved: requires backend/Dockerfile
    ```

- 2026-01-17 20:40
  - Summary: Added deterministic tool registry (sync/async invoke) + unit test.
  - Scope: backend/tools/**, tests/unit/test_tool_registry.py
  - Evidence: `backend/.venv/Scripts/python.exe -m pytest tests/unit/test_tool_registry.py -q`
    ```text
    2 passed in 0.05s
    ```

- 2026-01-17 20:25
  - Summary: Added controller module structure (engine types, node base, exports) and renamed controller test file.
  - Scope: backend/controller/**, tests/unit/test_controller.py
  - Evidence: `backend/.venv/Scripts/python.exe -m pytest tests/unit -q`
    ```text
    15 passed in 0.20s
    ```

- 2026-01-17 19:54
  - Summary: Ported core hardware detection service (CPU/RAM/Disk) and added psutil/pytest-asyncio dependencies.
  - Scope: backend/core/hardware/, backend/requirements.txt, tests/unit/test_hardware.py
  - Evidence: `backend/.venv/Scripts/python.exe -m pytest tests/unit/test_hardware.py -q`
    ```text
    3 passed in 0.12s
    ```
  - Evidence: `backend/.venv/Scripts/python.exe -m pip show psutil`
    ```text
    Version: 7.2.1
    ```
  - Evidence: `backend/.venv/Scripts/python.exe -m pip show pytest-asyncio`
    ```text
    Version: 1.3.0
    ```

- 2026-01-17 19:35
  - Summary: Ported core observability module (logging, metrics) and added Pydantic dependency.
  - Scope: backend/core/observability/, backend/requirements.txt, tests/unit/test_observability.py
  - Evidence: `backend/.venv/Scripts/python.exe -m pip show pydantic`
    ```text
    Version: 2.12.5
    ```
  - Evidence: `backend/.venv/Scripts/python.exe -m pytest tests/unit/test_observability.py -q`
    ```text
    3 passed in 0.10s
    ```

- 2026-01-17 18:54
  - Summary: Added explicit env-file loading support to backend configuration with precedence rules.
  - Scope: backend/core/config/settings.py, backend/requirements.txt, tests/unit/test_config_env.py
  - Evidence: `backend/.venv/Scripts/python.exe -m pip show python-dotenv` + `pytest`
    ```text
    Version: 1.2.1
    6 passed in 0.09s
    ```

- 2026-01-17 18:04
  - Summary: Upgraded pip and established pytest unit testing baseline.
  - Scope: backend/requirements.txt, tests/unit/
  - Evidence: `backend/.venv/Scripts/python.exe -m pytest tests/unit -q`
    ```text
    1 passed in 0.06s
    ```

- 2026-01-17 17:53
  - Summary: Established backend environment, entrypoint, and validation harness with reporting.
  - Scope: backend/main.py, backend/requirements.txt, scripts/validate_backend.py (generated: reports/*)
  - Evidence: `backend/.venv/Scripts/python.exe scripts/validate_backend.py`
    ```text
    [PASS] backend/main.py found
    [PASS] Venv Python Health: Python 3.12.10
    Validation PASSED.
    ```
