# SYSTEM_INVENTORY.md

Authoritative capability ledger. This is not a roadmap or config reference.

## Rules
- One entry = one capability, validated at a point in time.
- Entries must include: Capability, State, Location, Validation. Notes optional (1 line max).
- Do not include environment values, wiring details, or implementation notes.
- Append-only. Do not edit or delete prior entries.
- New capabilities go at the top under `## Inventory`.
- Corrections or clarifications go **only** in the Appendix section.

## States
- Planned: intent only, not implemented
- Implemented: code exists, not yet validated end-to-end
- Verified: validated with evidence (command + excerpt)
- Deferred: intentionally postponed (reason noted)

## Inventory

- **Capability**: VoiceSession artifact + validation-only replay contract (references archived task steps, verifies tool alignment)
  - **State**: Verified
  - **Location**: `backend/core/controller.py`, `backend/memory/working_state.py`, `tests/agentic/test_voice_session_replay.py`
  - **Validation**: `backend/.venv/Scripts/python scripts/validate_backend.py`
    ```text
    Unit Tests:        PASS
    Integration Tests: PASS
    Agentic Tests:     PASS
    ✅ JARVISv4 Current ./backend is validated!
    ```

- **Capability**: End-to-end voice lifecycle orchestration (wake_word → capture → STT → agent → TTS → archive) with deterministic archival and failure semantics
  - **State**: Verified
  - **Location**: `backend/core/controller.py`, `tests/agentic/test_voice_lifecycle_orchestration.py`
  - **Validation**: `backend/.venv/Scripts/python scripts/validate_backend.py`
    ```text
    Unit Tests:        PASS
    Integration Tests: PASS
    Agentic Tests:     PASS
    ✅ JARVISv4 Current ./backend is validated!
    ```

- **Capability**: Voice API endpoints (STT/TTS/Wake Word) as pass-through wrappers over voice tools
  - **State**: Verified
  - **Location**: `backend/api/app.py`, `backend/api/models.py`, `backend/tools/voice.py`
  - **Validation**: `backend/.venv/Scripts/python scripts/validate_backend.py`
    ```text
    Unit Tests:        PASS
    Integration Tests: PASS
    Agentic Tests:     PASS
    ✅ JARVISv4 Current ./backend is validated!
    ```

- **Capability**: openWakeWord provisioning under MODEL_PROVISIONING_POLICY (strict=no provisioning; on_demand/startup invoke library downloader) with deterministic provisioning artifacts
  - **State**: Verified
  - **Location**: `backend/core/voice/runtime.py`, `tests/unit/test_voice_runtime.py`
  - **Validation**: `backend/.venv/Scripts/python scripts/validate_backend.py`
    ```text
    Unit Tests:        PASS
    Integration Tests: PASS
    Agentic Tests:     PASS
    ✅ JARVISv4 Current ./backend is validated!
    ```

- **Capability**: Wake-word detection via openWakeWord with deterministic artifacts and strict provisioning semantics
  - **State**: Verified
  - **Location**: `backend/core/voice/runtime.py`, `backend/tools/voice.py`, `tests/unit/test_voice_runtime.py`, `tests/unit/test_voice_tool.py`
  - **Validation**: `backend/.venv/Scripts/python scripts/validate_backend.py`

- **Capability**: Unified voice model provisioning policy (strict default) with deterministic provisioning metadata
  - **State**: Verified
  - **Location**: `backend/core/config/settings.py`, `backend/core/model_manager.py`, `backend/core/voice/runtime.py`
  - **Validation**: `backend/.venv/Scripts/python scripts/validate_backend.py`

- **Capability**: Controller trace store closes SQLite handles deterministically
  - **State**: Verified
  - **Location**: `backend/memory/stores/trace_store.py`
  - **Validation**: `backend/.venv/Scripts/python scripts/validate_backend.py`

- **Capability**: Controller executes plans via WorkflowEngine
  - **State**: Verified
  - **Location**: `backend/core/controller.py`, `backend/controller/engine/engine.py`
  - **Validation**: `python scripts/validate_backend.py`
  - **Notes**: New integration test file `tests/integration/test_controller_workflow_integration.py` proves deterministic output and error handling when controller uses WorkflowEngine for step execution

- **Capability**: Enhanced WorkflowEngine with v3 execution logic
  - **State**: Verified
  - **Location**: `backend/controller/engine/engine.py`
  - **Evidence**: All 12 workflow engine tests pass, full backend validation passes
  - **Notes**: Linear workflow execution with dependency ordering, state tracking, and error handling

- **Piper Model Presence & Placement Contract (TTS)**
  - State: Verified
  - Location: `backend/core/voice/runtime.py`, `backend/tools/voice.py`, `tests/unit/test_voice_tool.py`
  - Validation: `python scripts/validate_backend.py`
  - Notes: Implements `MODEL_PATH` + `piper/{voice}.onnx` resolution contract with deterministic artifact reporting, preserving B1 deferred execution behavior. Requires local LLM (Ollama) running for full regression suite validation.

- **Whisper Model Presence Contract (STT)**
  - State: Verified
  - Location: `backend/core/voice/runtime.py`, `backend/tools/voice.py`, `tests/unit/test_voice_tool.py`
  - Validation: `backend/.venv/Scripts/python -m pytest -q tests/unit/test_voice_tool.py -rs`
  - Notes: Deterministic preflight model check with explicit artifact fields (`model_found`, `model_required`, `model_error`).

- **Voice Artifact Contract (STT/TTS I/O)**
  - State: Verified
  - Location: `backend/core/voice/runtime.py`, `tests/unit/test_voice_tool.py`
  - Validation: `backend/.venv/Scripts/python -m pytest -q tests/unit/test_voice_runtime.py tests/unit/test_voice_tool.py -rs`
  - Notes: Runtime now returns deterministic structured payloads with `mode`, `input`, and `artifacts` keys for both STT (transcript_text) and TTS (audio_path) operations.

- **Docker E2E Voice Invocation**
  - State: Verified
  - Location: `docker-compose.dev.yml`, `docker-compose.yml`, `tests/agentic/test_deterministic_voice_tools.py`
  - Validation:
    - `docker compose -f docker-compose.dev.yml run --rm validate-voice`
    - `docker compose -f docker-compose.yml run --rm validate-voice`
  - Notes: Deterministic voice invocation validated inside dev and hardened prod containers.

- **Voice Invocation in Agent Execution Flow**
  - State: Verified
  - Location: `backend/core/controller.py`, `tests/agentic/test_deterministic_voice_tools.py`
  - Validation: `backend/.venv/Scripts/python -m pytest tests/agentic/test_deterministic_voice_tools.py -q`
  - Notes: Registers `voice_stt` and `voice_tts` in the `ECFController` tool registry and validates their invocation via a deterministic execution path with injected plans and mocked LLM logic.

- **Voice Tool Integration (ECF)**
  - State: Verified
  - Location: `backend/tools/voice.py`, `tests/unit/test_voice_tool.py`
  - Validation: `backend/.venv/Scripts/python -m pytest tests/unit/test_voice_tool.py -v`
  - Notes: ECF-facing voice tools (voice_stt, voice_tts) that wrap Phase B1 runtime with ToolRegistry integration, JSON schema validation, and deterministic structured result returns.

- **Voice Runtime Execution Plumbing**
  - State: Verified
  - Location: `backend/core/voice/runtime.py`, `tests/unit/test_voice_runtime.py`
  - Validation: `backend/.venv/Scripts/python -m pytest tests/unit/test_voice_runtime.py -v`
  - Notes: Minimal subprocess-based execution of whisper (STT) and piper (TTS) binaries with structured result capture and comprehensive error handling.

- **Prod Voice Container Substrate**
  - State: Verified
  - Location: `backend/Dockerfile`, `docker-compose.yml`
  - Validation:
    - `docker compose -f docker-compose.yml build backend`
    - `docker compose -f docker-compose.yml run --rm backend whisper --help`
    - `docker compose -f docker-compose.yml run --rm backend piper --help`
  - Notes: Hardened prod container with non-root user, read-only filesystem, and voice binary executability.

- **Dev Voice Container Substrate**
  - State: Verified
  - Location: `backend/Dockerfile.dev`, `docker-compose.dev.yml`
  - Validation:
    - `docker compose -f docker-compose.dev.yml build backend`
    - `docker compose -f docker-compose.dev.yml run --rm backend whisper --help`
    - `docker compose -f docker-compose.dev.yml run --rm backend piper --help`
  - Notes: Dev-only container capability proving executability of legacy voice binaries (`whisper`, `piper`).

- **Multi-Task Orchestration (Analytics-Driven Termination)**
  - State: Verified
  - Location: `backend/core/controller.py`, `tests/agentic/test_ecf_core_flow.py`
  - Validation: `backend/.venv/Scripts/python -m pytest tests/agentic/test_ecf_core_flow.py::test_orchestrate_task_batch_terminates_on_failure_via_analytics -q`
  - Notes: Runs a bounded batch of sequential tasks using deterministic `text_output` execution and stops on the first failure observed via `summarize_task_outcomes()`; test proves mixed outcomes (COMPLETED + FAILED) and no dangling ACTIVE task artifacts.

- **Planning/Execution Step Bounds (MAX_PLANNED_STEPS / MAX_EXECUTED_STEPS)**
  - State: Verified
  - Location: `backend/core/controller.py`, `tests/unit/test_ecf_controller.py`
  - Validation: `backend/.venv/Scripts/python -m pytest tests/unit/test_ecf_controller.py::test_controller_rejects_plan_exceeding_max_planned_steps tests/unit/test_ecf_controller.py::test_controller_fails_when_max_executed_steps_exceeded -q`
  - Notes: Planning fails fast with `failure_cause=planning_invalid` when `next_steps` exceeds the cap; execution fails with `failure_cause=execution_step_failed` only when work remains (cap checked after empty `next_steps` guard). Defaults are 100; tests monkeypatch the limits.

- **Supervisor Watchdog Policy (Resume IN_PROGRESS Only)**
  - State: Verified
  - Location: `backend/core/controller.py`, `tests/agentic/test_supervisor_watchdog_resume.py`
  - Validation: `backend/.venv/Scripts/python -m pytest tests/agentic/test_supervisor_watchdog_resume.py -q`
  - Notes: `supervisor_resume_stalled_tasks` deterministically resumes only ACTIVE tasks that are stalled (no `current_step`) and already in `IN_PROGRESS`; it skips `CREATED` tasks (never started) to keep the watchdog recovery-oriented.

- **Typed Task Failure Causes (failure_cause + error in task artifacts)**
  - State: Verified
  - Location: `backend/core/controller.py`, `tests/unit/test_ecf_controller.py`
  - Validation: `backend/.venv/Scripts/python -m pytest tests/unit/test_ecf_controller.py::test_controller_planning_failure -q`
  - Notes: FAILED task artifacts now persist `failure_cause` (coarse values: `planning_invalid`, `execution_step_failed`, `controller_error`) and also persist `error` across planning, execution-step, and controller-exception failure paths.

- **Deterministic Text Output Tool (text_output)**
  - State: Verified
  - Location: `backend/tools/text_output.py`, `backend/core/controller.py`, `tests/agentic/test_deterministic_text_output_tool.py`
  - Validation: `backend/.venv/Scripts/python -m pytest tests/agentic/test_deterministic_text_output_tool.py -q`
  - Notes: Provides a deterministic, side-effect-free executor tool for returning literal text; supports end-to-end task completion validation without external dependencies.

- **Proxy Readiness Primitives (Health + API Prefix)**
  - State: Verified
  - Location: `backend/api/app.py`
  - Validation: `backend/.venv/Scripts/python -m uvicorn backend.api.app:app --port 8000` (with `API_PREFIX=/api`) + `curl.exe -s -i http://127.0.0.1:8000/healthz` + `curl.exe -s -i http://127.0.0.1:8000/api/healthz`
  - Notes: Provides health probe and optional prefixed routing for proxy setup; does not imply Nginx is implemented.

- **API Task Response Contract (POST /v1/tasks)**
  - State: Verified
  - Location: `backend/api/app.py`, `backend/api/models.py`, `backend/core/controller.py`
  - Validation: `backend/.venv/Scripts/python -m uvicorn backend.api.app:app --port 8000` + `curl.exe -s -X POST http://127.0.0.1:8000/v1/tasks -H "Content-Type: application/json" -d '{"goal":"ping"}'`
  - Notes: Failure responses preserve a durable task_id and include an explicit error field; this does not imply LLM connectivity success.

- **Redis Cache Integration (WebSearchTool)**
  - State: Verified
  - Location: `backend/core/cache/redis_cache.py`, `backend/core/config/settings.py`, `backend/tools/web_search.py`, `tests/unit/test_web_search.py`
  - Validation: `backend/.venv/Scripts/python -m pytest tests/unit/test_web_search.py -q`
  - Notes: Web search results are cached via Redis when `REDIS_URL` is configured; unit tests assert cache hit behavior without Docker.

- **Tier-2 Episodic Trace (Append-Only)**
  - State: Verified
  - Location: `backend/memory/stores/trace_store.py`, `backend/core/controller.py`, `tests/unit/test_ecf_controller.py`
  - Validation: `backend/.venv/Scripts/python -m pytest tests/unit/test_ecf_controller.py -q`
  - Notes: Controller emits decision/tool/validation trace rows into SQLite (append-only) during standard task execution.

- **CLI LLM Preflight (Ollama / OpenAI-compatible)**
  - State: Verified
  - Location: `backend/main.py`
  - Validation: `backend/.venv/Scripts/python -m backend.main --check-llm --llm-base-url http://localhost:11434/v1 --llm-model llama3.1:8b --llm-timeout-seconds 5 --llm-max-retries 0`
  - Validation: `backend/.venv/Scripts/python -m backend.main --check-llm --llm-base-url http://localhost:1/v1 --llm-model llama3.1:8b --llm-timeout-seconds 2 --llm-max-retries 0`
  - Notes: Preflight uses `AsyncOpenAI(max_retries=0)` and `models.list()` for a lightweight connectivity check; failure output includes category and underlying exception type/message.

- **Tool Registry (Contract Hardening)**
  - State: Verified
  - Location: `backend/tools/registry/registry.py`, `tests/unit/test_tool_registry.py`
  - Validation: `backend/.venv/Scripts/python -m pytest tests/unit/test_tool_registry.py -q`
  - Validation: `backend/.venv/Scripts/python -m pytest tests/unit/test_executor.py -q`
  - Notes: Tool-call boundary now yields deterministic typed failures with stable messages for unknown tools, schema-invalid params, and tool execution errors.

- **Governance Scaffolding**
  - State: Verified
  - Location: `AGENTS.md`, `CHANGE_LOG.md`, `SYSTEM_INVENTORY.md`, `Project.md`, `.clinerules/`
  - Validation: `ls; ls .clinerules`

- **Backend Baseline**
  - State: Verified
  - Location: `backend/requirements.txt`, `backend/main.py`, `backend/.venv/`
  - Validation: `backend/.venv/Scripts/python.exe backend/main.py`

- **Validation Harness (Backend)**
  - State: Verified
  - Location: `scripts/validate_backend.py`, `reports/`
  - Validation: `backend/.venv/Scripts/python.exe scripts/validate_backend.py`

- **Unit Testing Baseline**
  - State: Verified
  - Location: `tests/unit/`, `backend/requirements.txt`
  - Validation: `backend/.venv/Scripts/python.exe -m pytest tests/unit -q`

- **Venv Toolchain**
  - State: Verified
  - Location: `backend/.venv/`, `backend/requirements.txt`
  - Validation: `backend/.venv/Scripts/python.exe -m pip --version; backend/.venv/Scripts/python.exe -m pip show pytest`

- **Config Env Loading**
  - State: Verified
  - Location: `backend/core/config/settings.py`, `backend/requirements.txt`
  - Validation: `backend/.venv/Scripts/python.exe -m pip show python-dotenv`
  - Validation: `backend/.venv/Scripts/python.exe -m pytest tests/unit -q`

- **Observability Foundation**
  - State: Verified
  - Location: `backend/core/observability/`, `backend/requirements.txt`
  - Validation: `backend/.venv/Scripts/python.exe -m pip show pydantic`
  - Validation: `backend/.venv/Scripts/python.exe -m pytest tests/unit/test_observability.py -q`

- **Hardware Detection Service**
  - State: Verified
  - Location: `backend/core/hardware/`, `backend/requirements.txt`
  - Validation: `backend/.venv/Scripts/python.exe -m pip show psutil`
  - Validation: `backend/.venv/Scripts/python.exe -m pip show pytest-asyncio`
  - Validation: `backend/.venv/Scripts/python.exe -m pytest tests/unit/test_hardware.py -q`

- **Controller Foundation**
  - State: Verified
  - Location: `backend/controller/`, `tests/unit/test_controller.py`
  - Validation: `backend/.venv/Scripts/python.exe -m pytest tests/unit -q`

- **Tool Registry**
  - State: Verified
  - Location: `backend/tools/registry/`, `tests/unit/test_tool_registry.py`
  - Validation: `backend/.venv/Scripts/python.exe -m pytest tests/unit/test_tool_registry.py -q`

- **Root Config Templates**
  - State: Verified
  - Location: `.env.example`, `.env.dev.example`, `docker-compose.yml`, `docker-compose.dev.yml`
  - Validation: `ls .env.example, .env.dev.example, docker-compose.yml, docker-compose.dev.yml`

- **Memory Foundation (In-Memory Store)**
  - State: Verified
  - Location: `backend/memory/`, `tests/unit/test_memory_store.py`
  - Validation: `backend/.venv/Scripts/python.exe -m pytest tests/unit/test_memory_store.py -q`

- **Node Execution Path**
  - State: Verified
  - Location: `backend/controller/engine/engine.py`, `backend/controller/nodes/callable.py`, `tests/unit/test_node_execution.py`
  - Validation: `backend/.venv/Scripts/python.exe -m pytest tests/unit/test_node_execution.py -q`

- **Context Boundary Hardening**
  - State: Verified
  - Location: `.clineignore`
  - Validation: `ls .clineignore`
  - Notes: Blocks heavy reference symlinks and venv; shifts reference/ to opt-in via @mention.

- **Memory Integration Node**
  - State: Verified
  - Location: `backend/controller/nodes/memory_op.py`, `tests/unit/test_memory_node.py`
  - Validation: `backend/.venv/Scripts/python.exe -m pytest tests/unit/test_memory_node.py -q`
  - Notes: Deterministic MemoryWriteNode that writes to MemoryItem schemas via WorkflowEngine context.

- **Workflow Execution (Sequence)**
  - State: Verified
  - Location: `backend/controller/engine/engine.py`, `backend/controller/nodes/memory_op.py`, `tests/unit/test_workflow_execution.py`
  - Validation: `backend/.venv/Scripts/python.exe -m pytest tests/unit/test_workflow_execution.py -q`

- **TaskContext Enforcement**
  - State: Verified
  - Location: `backend/controller/engine/types.py`, `backend/controller/engine/engine.py`, `backend/controller/nodes/`, `tests/unit/`
    - Validation: `backend/.venv/Scripts/python.exe scripts/validate_backend.py`

- **Episodic Memory (SQLite Store)**
  - State: Verified
  - Location: `backend/memory/stores/sqlite_store.py`, `tests/integration/test_sqlite_memory_store.py`
  - Validation: `backend/.venv/Scripts/python.exe -m pytest tests/integration -q`
  - Validation: `backend/.venv/Scripts/python.exe scripts/validate_backend.py` (with UTF-8 env)
  - Notes: Validates persistence across instance restarts (write -> restart -> read).

- **Memory Persistence (SQLite via Factory)**
  - State: Verified
  - Location: `backend/memory/stores/sqlite_store.py`, `backend/memory/factory.py`, `backend/core/config/settings.py`, `tests/integration/test_workflow_persistence.py`
  - Validation: `backend/.venv/Scripts/python.exe -m pytest tests/integration -q`
  - Validation: `backend/.venv/Scripts/python.exe scripts/validate_backend.py`

- **Tier 1 Working State Manager (Ephemeral)**
  - State: Verified
  - Location: `backend/memory/working_state.py`, `tests/unit/test_working_state.py`
  - Validation: `backend/.venv/Scripts/python.exe -m pytest tests/unit/test_working_state.py -q`
  - Validation: `backend/.venv/Scripts/python.exe scripts/validate_backend.py`
  - Notes: Implements ECF Tier 1 memory using JSON for ephemeral task state tracking with atomic writes and schema validation.

- **Planner Agent**
  - State: Verified
  - Location: `backend/agents/planner/planner.py`, `tests/unit/test_planner.py`
  - Validation: `backend/.venv/Scripts/python.exe -m pytest tests/unit/test_planner.py -q`
  - Validation: `python scripts/verify_planner_integration.py`
  - Notes: Stateless reasoning component integrated with `OpenAIProvider`. Verified to produce valid DAG task files in `tasks/`.

- **LLM Provider Service**
  - State: Verified
  - Location: `backend/core/llm/`, `scripts/test_llm_connectivity.py`
  - Validation: `pytest tests/unit/test_llm_provider.py` (5/5 PASS)
  - Validation: `python scripts/test_llm_connectivity.py` (Smoke Test)
  - Notes: Foundational LLM interface supporting OpenAI-compatible endpoints (Ollama, vLLM, Cloud). Includes exponential backoff retries.

- **Tool Registry**
  - State: Verified
  - Location: `backend/tools/registry/`, `backend/tools/base.py`
  - Validation: `pytest tests/unit/test_executor.py` (Indirectly via Executor)
  - Notes: Rich tool registry supporting metadata discovery for LLMs and JSON Schema validation for parameters.

- **Executor Agent**
  - State: Verified
  - Location: `backend/agents/executor/executor.py`, `tests/unit/test_executor.py`
  - Validation: `pytest tests/unit/test_executor.py` (3/3 PASS)
  - Validation: `python scripts/verify_executor_integration.py` (Smoke Test)
  - Notes: Tactical agent responsible for tool selection and invocation. Includes fallback logic for unmatched requests.

- **ECF Controller**
  - State: Verified (Audit Date: 2026-01-19)
  - Location: `backend/core/controller.py`, `backend/main.py`
  - Validation: `pytest tests/unit/test_ecf_controller.py`, `pytest tests/agentic/test_ecf_core_flow.py`
  - Notes: Authoritative FSM "Cognitive Spine" coordinating State, Planning, and Execution. Supports CLI goal execution. Validated via formal unit and E2E agentic tiers.

- **Episode Curator**
  - State: Verified (Audit Date: 2026-01-19)
  - Location: `backend/learning/curator.py`, `backend/datasets/`
  - Validation: `pytest tests/unit/test_curator.py`
  - Notes: Extracts high-quality Alpaca-style training data from archived task traces. Instrumented to capture tool name and parameters.

- **Basal Dataset**
  - State: Verified (Audit Date: 2026-01-19)
  - Location: `data/training/basal_set.json`
  - Validation: `pytest tests/unit/test_mixer.py` (via integration)
  - Notes: Anchor dataset of 5 "Golden Examples" (2 Planner, 3 Executor) to prevent catastrophic forgetting.

- **Dataset Mixer**
  - State: Verified (Audit Date: 2026-01-19)
  - Location: `backend/learning/mixer.py`
  - Validation: `pytest tests/unit/test_mixer.py`
  - Notes: Handles the weighted blending of new curriculum data with basal anchor data; includes oversampling and shuffling.

- **Regression Suite**
  - State: Verified
  - Location: `backend/learning/regression.py`, `tests/unit/test_regression.py`
  - Validation: `.\backend\.venv\Scripts\python -m pytest -s -vv --log-cli-level=INFO tests/unit/test_regression.py`
  - Notes: Verified production component for mining "Golden" episodes from SQLite and performing semantic LLM-based validation using local qwen2.5-coder:7b.

- **Learner (Orchestrator)**
  - State: Verified (Audit Date: 2026-01-19)
  - Location: `backend/learning/train.py`, `backend/learning/config.yaml`
  - Validation: `pytest tests/integration/test_learner_pipeline.py`
  - Notes: Training pipeline orchestrator that coordinates dataset mixing and trainer initialization. Supports LoRA hyperparameter configuration and lightweight dry-run validation.

- **Full Learning Cycle**
  - State: Verified (Audit Date: 2026-01-21)
  - Location: `tests/integration/test_learning_cycle.py`
  - Validation: `.\backend\.venv\scripts\python scripts/validate_backend.py`
  - Notes: End-to-end proof of ECF Learning Loop: Task Execution (Trace Generation) -> Episode Curation (Data Extraction) -> Dataset Mixing (Blend with Basal) -> Training Orchestration (Dry Run).

- **Privacy Engine (Port)**
  - State: Verified (Audit Date: 2026-01-21)
  - Location: `backend/core/privacy.py`, `tests/unit/test_privacy.py`
  - Validation: `.\backend\.venv\scripts\python scripts/validate_backend.py`
  - Notes: Consolidated v2 Encryption (AES-GCM/PBKDF2) and v3 Compliance (Classification/Redaction/Audit). Replaced `pycryptodome` with `cryptography` library.

- **Semantic Memory (Tier 3)**
  - State: Verified (Audit Date: 2026-01-21)
  - Location: `backend/memory/stores/semantic.py`, `tests/unit/test_semantic_memory.py`
  - Validation: `.\backend\.venv\scripts\python scripts/validate_backend.py`
  - Notes: Implements ECF Tier 3 hybrid memory using Scikit-Learn (vector similarity) and SQLite (symbolic metadata). Optimized for clean, warning-free execution on Python 3.12.

- **Budget Service (Safety Limits)**
  - State: Verified (Audit Date: 2026-01-21)
  - Location: `backend/core/budget.py`, `backend/core/config/settings.py`
  - Validation: `backend/.venv/Scripts/python.exe -m pytest tests/unit/test_budget.py`
  - Notes: Ports v2 Budget Service for granular cost tracking and enforcement. Uses SQLite for persistence with daily reset logic. Supports 'none', 'log', and 'block' enforcement levels.

- **Unified Search Tool**
  - State: Verified (Audit Date: 2026-01-22)
  - Location: `backend/tools/web_search.py`, `backend/core/search_providers.py`, `tests/unit/test_web_search.py`
  - Validation: `backend/.venv/Scripts/python.exe scripts/validate_backend.py`
  - Notes: Deterministic Web Search tool with multi-provider support (DuckDuckGo, Bing, Tavily, Google). Features integrated Privacy Redaction (PII scrubbing) and Budget enforcement.

- **Validate Gate (API Smoke Probe)**
  - State: Verified
  - Location: `scripts/validate_backend.py`
  - Validation: `backend/.venv/Scripts/python.exe scripts/validate_backend.py`
  - Notes: Validates API process starts/responds to /healthz and /metrics; does not imply production readiness.

- **RedisCache (Injectable Client Boundary + JSON Round-Trip)**
  - State: Verified
  - Location: `backend/core/cache/redis_cache.py`, `tests/unit/test_redis_cache.py`
  - Validation: `backend/.venv/Scripts/python -m pytest tests/unit/test_redis_cache.py -q`
 - Notes: Verifies RedisCache JSON serialization and get/setex interaction via an injected fake client; does not validate live Redis connectivity.

- **Task Resume from Artifacts (Controller + CLI)**
  - State: Verified
  - Location: `backend/core/controller.py`, `backend/memory/working_state.py`, `backend/main.py`, `tests/agentic/test_task_resume.py`
  - Validation: `backend/.venv/Scripts/python -m pytest tests/agentic/test_task_resume.py -q`
  - Notes: Resumes an existing task_id by continuing remaining `next_steps` from the on-disk task JSON; fails fast if `current_step` is non-null; does not imply safe handling of in-flight step side effects.

- **Task Supervision Surface (List Tasks: ACTIVE + ARCHIVED)**
  - State: Verified
  - Location: `backend/memory/working_state.py`, `backend/core/controller.py`, `backend/main.py`, `tests/agentic/test_task_supervision_list_tasks.py`
  - Validation: `backend/.venv/Scripts/python -m pytest tests/agentic/test_task_supervision_list_tasks.py -q`
  - Notes: Read-only listing enumerates task JSON artifacts from `tasks/` (ACTIVE) and `tasks/archive/**` (ARCHIVED) and reports deterministic ordering (ACTIVE first, then task_id ascending).

- **Task ID Ownership (Controller-Authoritative; No Dual Task Creation)**
  - State: Verified
  - Location: `backend/core/controller.py`, `backend/agents/planner/planner.py`, `tests/agentic/test_ecf_core_flow.py`
  - Validation: `backend/.venv/Scripts/python -m pytest tests/agentic/test_ecf_core_flow.py::test_ecf_first_flight_e2e -q`
  - Notes: Confirms the Controller owns task_id deterministically; planning updates the existing task artifact rather than creating a second task.

- **CLI LLM Override Precedence (Flags → Controller Provider)**
  - State: Verified
  - Location: `backend/main.py`, `backend/core/controller.py`, `tests/unit/test_cli_llm_overrides.py`
  - Validation: `backend/.venv/Scripts/python -m pytest tests/unit/test_cli_llm_overrides.py -q`
  - Notes: Confirms CLI-resolved `llm_base_url`/`llm_model` settings and `--llm-timeout-seconds`/`--llm-max-retries` are forwarded into `OpenAIProvider(...)` used by `ECFController`, including the `max_retries=0` no-retry case.

- **Planning-Stage Tool Executability Guardrail (Fail Fast Before Execution)**
  - State: Verified
  - Location: `backend/core/controller.py`, `tests/unit/test_ecf_controller.py`
  - Validation: `backend/.venv/Scripts/python -m pytest tests/unit/test_ecf_controller.py::test_controller_rejects_plan_with_unknown_tool_fails_in_planning -q`
  - Notes: Validates each planned step is executable using the executor’s tool-selection logic before entering EXECUTING; if no tool matches, the task fails during PLANNING and is archived as FAILED with an `error` message recorded in the task state.

---

# Appendix: 
## Only Clarifications and Corrections below
- Use this section to correct or narrow the meaning of a prior inventory entry.
- Do not restate full validation evidence here.
- Reference the original capability by name and date.
- Corrections clarify scope or semantics; they do not introduce new capabilities.

## Inventory Wording Normalization — 2026-01-23

- **ECF Controller (Clarification)**
  - Clarification: The agentic “first flight” test uses mocked LLM responses and verifies planning → execution → archiving behavior plus artifact persistence. Unit tests cover controller components. This evidence does not establish full architectural completeness beyond the current control loop.
  - Evidence: `tests/agentic/test_ecf_core_flow.py`, `backend/core/controller.py`

- **Regression Suite (Clarification)**
  - Clarification: Implements an LLM-judge regression evaluator over mined SQLite task metadata and is validated by unit tests. End-to-end tests depend on an available OpenAI-compatible endpoint (e.g., local Ollama). Production readiness is not established by these tests alone.
  - Evidence: `backend/learning/regression.py`, `tests/unit/test_regression.py`

- **Full Learning Cycle (Clarification)**
  - Clarification: Integration coverage demonstrates task trace generation → episode curation → dataset mixing → training orchestration (dry-run). It does not evidence a full fine-tune + deploy workflow.
  - Evidence: `tests/integration/test_learning_cycle.py` (via `scripts/validate_backend.py` entry)

- **Semantic Memory (Tier 3) (Clarification)**
  - Clarification: Implements tier-3 semantic memory using SentenceTransformer embeddings with sklearn nearest-neighbor retrieval persisted in SQLite. Unit tests validate init/add/retrieve/persistence/guardrails; runtime performance or “warning-free” claims are not evidenced here.
  - Evidence: `backend/memory/stores/semantic.py`, `tests/unit/test_semantic_memory.py`

## Memory Architecture Clarifications — 2026-01-23

- **Tier 1 Working State (Clarification)**
  - Clarification: Tier‑1 working state is implemented as JSON task files with required fields and atomic updates via `WorkingStateManager`. This reflects the current ephemeral task-state surface (create/update/complete/archive), not the full ECF memory contract beyond the fields enforced in `working_state.py`.
  - Evidence: `backend/memory/working_state.py`, `tests/unit/test_working_state.py`

- **Tier 2 Episodic Store (Clarification)**
  - Clarification: The current Tier‑2 persistence surface is a generic `SQLiteStore` that saves `MemoryItem` records into a single `memory_items` table (id/content/timestamp/metadata). It does **not** implement the richer episodic trace schema described in the ECF target (e.g., decisions/tool_calls/validations tables) within this repo snapshot.
  - Evidence: `backend/memory/stores/sqlite_store.py`, `backend/memory/schemas/memory.py`, `tests/integration/test_sqlite_memory_store.py`

- **Tier 2 Store Selection (Clarification)**
  - Clarification: `create_memory_store` selects between in‑memory and SQLite stores based on settings. This is a store factory, not a full episodic trace/logging subsystem.
  - Evidence: `backend/memory/factory.py`

- **Tier 3 Semantic Memory (Clarification)**
  - Clarification: Tier‑3 semantic memory is implemented using SentenceTransformer embeddings with sklearn `NearestNeighbors` plus SQLite tables for patterns/guardrails. This provides vector similarity + metadata filtering, but does not represent a FAISS-based or external vector DB tier in this repo.
  - Evidence: `backend/memory/stores/semantic.py`, `tests/unit/test_semantic_memory.py`

- **Memory Integration Node (Clarification)**
  - Clarification: The `MemoryWriteNode` integrates with the memory schemas and working state context, but does not on its own establish a complete three‑tier orchestration layer.
  - Evidence: `backend/controller/nodes/memory_op.py`, `tests/unit/test_memory_node.py`
