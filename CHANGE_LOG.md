# CHANGE_LOG.md

## Instructions
- Append-only record of reported work; corrections may be appended to entries.
- Write an entry only after the mini-phase objective is “done” and supported by evidence.
- No edits/reorders/deletes of past entries. If an entry is wrong, append a corrective entry.
- Each entry must include:
  - Timestamp: `YYYY-MM-DD HH:MM`
  - Summary: 1–2 lines, past tense
  - Scope: files/areas touched
  - Evidence: exact command(s) run + a minimal excerpt pointer (or embedded excerpt ≤10 lines)
- If a change is reverted, append a new entry describing the revert and why.

## Entries

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

- 2026-01-17 17:53
  - Summary: Established backend environment, entrypoint, and validation harness with reporting.
  - Scope: backend/main.py, backend/requirements.txt, scripts/validate_backend.py (generated: reports/*)
  - Evidence: `backend/.venv/Scripts/python.exe scripts/validate_backend.py`
    ```text
    [PASS] backend/main.py found
    [PASS] Venv Python Health: Python 3.12.10
    Validation PASSED.
    ```

- 2026-01-17 18:04
  - Summary: Upgraded pip and established pytest unit testing baseline.
  - Scope: backend/requirements.txt, tests/unit/
  - Evidence: `backend/.venv/Scripts/python.exe -m pytest tests/unit -q`
    ```text
    1 passed in 0.06s
    ```

- 2026-01-17 18:54
  - Summary: Added explicit env-file loading support to backend configuration with precedence rules.
  - Scope: backend/core/config/settings.py, backend/requirements.txt, tests/unit/test_config_env.py
  - Evidence: `backend/.venv/Scripts/python.exe -m pip show python-dotenv` + `pytest`
    ```text
    Version: 1.2.1
    6 passed in 0.09s
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

- 2026-01-17 20:25
  - Summary: Added controller module structure (engine types, node base, exports) and renamed controller test file.
  - Scope: backend/controller/**, tests/unit/test_controller.py
  - Evidence: `backend/.venv/Scripts/python.exe -m pytest tests/unit -q`
    ```text
    15 passed in 0.20s
    ```

- 2026-01-17 20:40
  - Summary: Added deterministic tool registry (sync/async invoke) + unit test.
  - Scope: backend/tools/**, tests/unit/test_tool_registry.py
  - Evidence: `backend/.venv/Scripts/python.exe -m pytest tests/unit/test_tool_registry.py -q`
    ```text
    2 passed in 0.05s
    ```

- 2026-01-17 21:05
  - Summary: Added env templates (v2-derived) and compose templates (v3-derived) with reserved annotations.
  - Scope: .env.example, .env.dev.example, docker-compose.yml, docker-compose.dev.yml
  - Evidence: `ls` + Excerpts
    ```text
    .env.example: # Privacy Settings (reserved: future capability)
    docker-compose.yml: # reserved: requires backend/Dockerfile
    ```

- 2026-01-18 05:48
  - Summary: Added memory schema + deterministic in-memory store + unit test.
  - Scope: backend/memory/**, tests/unit/test_memory_store.py
  - Evidence: `backend/.venv/Scripts/python.exe -m pytest tests/unit/test_memory_store.py -q`
    ```text
    2 passed in 0.07s
    ```

- 2026-01-18 06:07
  - Summary: Implemented single-node execution path + callable node; validated tool+memory interaction.
  - Scope: backend/controller/engine/engine.py, backend/controller/nodes/callable.py, tests/unit/test_node_execution.py
  - Evidence: `backend/.venv/Scripts/python.exe -m pytest tests/unit/test_node_execution.py -q`
    ```text
    1 passed in 0.07s
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

- 2026-01-18 08:26
  - Summary: Implemented MemoryWriteNode for deterministic memory operations and integrated with WorkflowEngine.
  - Scope: backend/controller/nodes/memory_op.py, tests/unit/test_memory_node.py
  - Evidence: `backend/.venv/Scripts/python.exe -m pytest tests/unit/test_memory_node.py -q`
    ```text
    .                                                                                                          [100%]
    1 passed in 0.10s
    ```

- 2026-01-18 09:45
  - Summary: Implemented ordered multi-node execution (`execute_sequence`) and added MemoryReadNode; validated via unit test.
  - Scope: backend/controller/engine/engine.py, backend/controller/nodes/memory_op.py, tests/unit/test_workflow_execution.py
  - Evidence: `backend/.venv/Scripts/python.exe -m pytest tests/unit/test_workflow_execution.py -q`
    ```text
    ..                                                                                                         [100%]
    2 passed in 0.08s
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

- 2026-01-19 14:54
  - Summary: Implemented `OpenAIProvider` with exponential backoff retries and support for local/cloud endpoints.
  - Scope: backend/core/llm/, backend/core/config/settings.py, backend/requirements.txt, scripts/test_llm_connectivity.py
  - Evidence: `pytest tests/unit/test_llm_provider.py` (5/5 PASS)
  - Evidence: `python scripts/test_llm_connectivity.py`
    ```text
    INFO:__main__:Received Response: Handshake Successful. I am ready.
    INFO:__main__:✅ SMOKE TEST PASSED: Handshake verified.
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

- 2026-01-19 19:48
  - Summary: Implemented DatasetMixer and RegressionSuite blueprint; scaffolded Basal Dataset with Golden Examples.
  - Scope: data/training/basal_set.json, backend/learning/mixer.py, backend/learning/regression.py, scripts/validate_mixer.py
  - Evidence: `backend/.venv/Scripts/python.exe scripts/validate_mixer.py`
    ```text
    Actual curriculum ratio: 70.00%
    Basal items (Golden) count: 6
    ✅ Validation Successful: 70/30 split achieved
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

- 2026-01-21 20:47
  - Summary: Implemented and verified Regression Suite with SQLite mining and LLM-based semantic judging.
  - Scope: backend/learning/regression.py, tests/unit/test_regression.py
  - Evidence: `.\backend\.venv\Scripts\python -m pytest tests/unit/test_regression.py`
    ```text
    tests\unit\test_regression.py ..                                         [100%]
    2 passed in 36.46s
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

- 2026-01-21 21:52
  - Summary: Realized Full ECF Learning Cycle via integrated validation test; fixed PYTHONPATH issue in initial sanity test.
  - Scope: tests/integration/test_learning_cycle.py, tests/unit/test_initial_sanity.py
  - Evidence: `.\backend\.venv\scripts\python scripts/validate_backend.py`
    ```text
    ✓ PASS: tests.unit.test_initial_sanity::test_backend_main_execution
    ✓ PASS: tests.integration.test_learning_cycle::test_full_learning_cycle
    ✅ JARVISv4 Current ./backend is validated!
    ```

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

- 2026-01-21 22:33
  - Summary: Implemented Memory Tier 3 (Semantic Memory) using FAISS and SQLite.
  - Scope: backend/memory/stores/semantic.py, tests/unit/test_semantic_memory.py, backend/requirements.txt
  - Evidence: `.\backend\.venv\scripts\python scripts/validate_backend.py` (All tests passed, including 6 new unit tests for semantic memory)

- 2026-01-21 22:45
  - Summary: Ported Budget Service from v2 to v4 for granular cost tracking and safety limits.
  - Scope: backend/core/budget.py, backend/core/config/settings.py, tests/unit/test_budget.py
  - Evidence: `backend/.venv/Scripts/python.exe -m pytest tests/unit/test_budget.py`
    ```text
    tests\unit\test_budget.py ........                                                                 [100%]
    8 passed in 0.13s
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

## Evidence Reproducibility Clarifications — 2026-01-23

- Clarification: Entries dated 2026-01-19 citing `scripts/test_llm_connectivity.py`, `scripts/verify_planner_integration.py`, `scripts/verify_executor_integration.py`, `scripts/first_flight.py`, `scripts/validate_curator.py`, and `scripts/validate_mixer.py` reference evidence commands whose script files are not present in the current repo tree. As of 2026-01-23, `scripts/` contains only `validate_backend.py`, so those specific evidence commands are not reproducible from this checkout.
  - Evidence: `ls scripts/`

- Clarification: Entries that reference validation report files under `reports/` (e.g., 2026-01-17 17:53) cannot be re-verified by agents under current governance because `.clineignore` blocks access to `reports/` contents. The artifacts may exist, but their contents are not reproducible through agent tooling in this context.
  - Evidence: root file listing showing `reports/` (🔒) and `.clineignore` includes `reports/`
