# SYSTEM_INVENTORY.md

## Instructions

- This document is a status snapshot of what exists and is validated now. It is not a roadmap.
- Additive updates only. Do not rewrite history. If a prior entry is wrong, append a correction with date + evidence pointer.
- Promote a capability only when supported by validation evidence (tests, harness runs, or reproducible runtime checks).
- Skips/warnings do not count as validation unless they are explicitly the intended outcome.
- Keep entries terse and concrete:
  - Capability name
  - Current state (pick one and use consistently)
  - Location (path(s))
  - Validation (exact command + minimal excerpt pointer)
  - Notes (optional, 1–2 lines)

## States

- Planned: intent only, not implemented
- Implemented: code exists, not yet validated end-to-end
- Verified: validated with evidence (command + excerpt)
- Deferred: intentionally postponed (reason noted)

## Inventory

- **Governance Scaffolding**
  - State: Verified
  - Location: `AGENTS.md`, `CHANGE_LOG.md`, `SYSTEM_INVENTORY.md`, `Project.md`, `.clinerules/`
  - Validation: `ls; ls .clinerules`
    ```text
    AGENTS.md
    CHANGE_LOG.md
    Project.md
    SYSTEM_INVENTORY.md
    .clinerules/
    00-guardrails.md
    10-mini-phase.md
    20-validation-tests.md
    30-doc-truth.md
    40-inventory-states.md
    50-change-log.md
    ```

- **Backend Baseline**
  - State: Verified
  - Location: `backend/requirements.txt`, `backend/main.py`, `backend/.venv/`
  - Validation: `backend/.venv/Scripts/python.exe backend/main.py`
    ```text
    JARVISv4 Backend initialized.
    ```

- **Validation Harness (Backend)**
  - State: Verified
  - Location: `scripts/validate_backend.py`, `reports/`
  - Validation: `backend/.venv/Scripts/python.exe scripts/validate_backend.py`
    ```text
    [PASS] backend/main.py found
    [PASS] Venv Python Health: Python 3.12.10
    Validation PASSED.
    Report saved to: reports\backend_validation_report_20260117_175319.txt
    ```

- **Unit Testing Baseline**
  - State: Verified
  - Location: `tests/unit/`, `backend/requirements.txt`
  - Validation: `backend/.venv/Scripts/python.exe -m pytest tests/unit -q`
    ```text
    .                                                                                                          [100%]
    1 passed in 0.06s
    ```

- **Venv Toolchain**
  - State: Verified
  - Location: `backend/.venv/`, `backend/requirements.txt`
  - Validation: `backend/.venv/Scripts/python.exe -m pip --version; backend/.venv/Scripts/python.exe -m pip show pytest`
    ```text
    pip 25.3 from E:\WORK\CODE\GitHub\bentman\Repositories\JARVISv4\backend\.venv\Lib\site-packages\pip (python 3.12)
    Version: 9.0.2
    ```

- **Config Env Loading**
  - State: Verified
  - Location: `backend/core/config/settings.py`, `backend/requirements.txt`
  - Validation: `backend/.venv/Scripts/python.exe -m pip show python-dotenv`
    ```text
    Version: 1.2.1
    ```
  - Validation: `backend/.venv/Scripts/python.exe -m pytest tests/unit -q`
    ```text
    ......                                                                                                     [100%]
    6 passed in 0.09s
    ```

- **Observability Foundation**
  - State: Verified
  - Location: `backend/core/observability/`, `backend/requirements.txt`
  - Validation: `backend/.venv/Scripts/python.exe -m pip show pydantic`
    ```text
    Version: 2.12.5
    ```
  - Validation: `backend/.venv/Scripts/python.exe -m pytest tests/unit/test_observability.py -q`
    ```text
    ...                                                                                                        [100%]
    3 passed in 0.10s
    ```

- **Hardware Detection Service**
  - State: Verified
  - Location: `backend/core/hardware/`, `backend/requirements.txt`
  - Validation: `backend/.venv/Scripts/python.exe -m pip show psutil`
    ```text
    Version: 7.2.1
    ```
  - Validation: `backend/.venv/Scripts/python.exe -m pip show pytest-asyncio`
    ```text
    Version: 1.3.0
    ```
  - Validation: `backend/.venv/Scripts/python.exe -m pytest tests/unit/test_hardware.py -q`
    ```text
    ...                                                                                                        [100%]
    3 passed in 0.12s
    ```

- **Controller Foundation**
  - State: Verified
  - Location: `backend/controller/`, `tests/unit/test_controller.py`
  - Validation: `backend/.venv/Scripts/python.exe -m pytest tests/unit -q`
    ```text
    ...............                                                                                            [100%]
    15 passed in 0.20s
    ```

- **Tool Registry**
  - State: Verified
  - Location: `backend/tools/registry/`, `tests/unit/test_tool_registry.py`
  - Validation: `backend/.venv/Scripts/python.exe -m pytest tests/unit/test_tool_registry.py -q`
    ```text
    ..                                                                                                         [100%]
    2 passed in 0.05s
    ```

- **Root Config Templates**
  - State: Verified
  - Location: `.env.example`, `.env.dev.example`, `docker-compose.yml`, `docker-compose.dev.yml`
  - Validation: `ls .env.example, .env.dev.example, docker-compose.yml, docker-compose.dev.yml`
    ```text
    .env.dev.example
    .env.example
    docker-compose.dev.yml
    docker-compose.yml
    ```

- **Memory Foundation (In-Memory Store)**
  - State: Verified
  - Location: `backend/memory/`, `tests/unit/test_memory_store.py`
  - Validation: `backend/.venv/Scripts/python.exe -m pytest tests/unit/test_memory_store.py -q`
    ```text
    ..                                                                     [100%]
    2 passed in 0.07s
    ```

- **Node Execution Path**
  - State: Verified
  - Location: `backend/controller/engine/engine.py`, `backend/controller/nodes/callable.py`, `tests/unit/test_node_execution.py`
  - Validation: `backend/.venv/Scripts/python.exe -m pytest tests/unit/test_node_execution.py -q`
    ```text
    .                                                                                                          [100%]
    1 passed in 0.07s
    ```

- **Context Boundary Hardening**
  - State: Verified
  - Location: `.clineignore`
  - Validation: `ls .clineignore`
    ```text
    -a---          2026-01-18  7:29 AM            275 .clineignore
    ```
  - Notes: Blocks heavy reference symlinks and venv; shifts reference/ to opt-in via @mention.

- **Memory Integration Node**
  - State: Verified
  - Location: `backend/controller/nodes/memory_op.py`, `tests/unit/test_memory_node.py`
  - Validation: `backend/.venv/Scripts/python.exe -m pytest tests/unit/test_memory_node.py -q`
    ```text
    .                                                                                                          [100%]
    1 passed in 0.10s
    ```
  - Notes: Deterministic MemoryWriteNode that writes to MemoryItem schemas via WorkflowEngine context.

- **Workflow Execution (Sequence)**
  - State: Verified
  - Location: `backend/controller/engine/engine.py`, `backend/controller/nodes/memory_op.py`, `tests/unit/test_workflow_execution.py`
  - Validation: `backend/.venv/Scripts/python.exe -m pytest tests/unit/test_workflow_execution.py -q`
    ```text
    ..                                                                                                         [100%]
    2 passed in 0.08s
    ```

- **TaskContext Enforcement**
  - State: Verified
  - Location: `backend/controller/engine/types.py`, `backend/controller/engine/engine.py`, `backend/controller/nodes/`, `tests/unit/`
    - Validation: `backend/.venv/Scripts/python.exe scripts/validate_backend.py`
    ```text
    SUCCESS: Unit: 23 tests
    Unit Tests:        PASS
    Integration Tests: WARN
    Agentic Tests:     WARN
    [INVARIANTS]
    UNIT_TESTS=PASS
    INTEGRATION_TESTS=WARN
    AGENTIC_TESTS=WARN
    ```

- **Episodic Memory (SQLite Store)**
  - State: Verified
  - Location: `backend/memory/stores/sqlite_store.py`, `tests/integration/test_sqlite_memory_store.py`
  - Validation: `backend/.venv/Scripts/python.exe -m pytest tests/integration -q`
    ```text
    ..                                                                       [100%]
    2 passed in 0.40s
    ```
  - Validation: `backend/.venv/Scripts/python.exe scripts/validate_backend.py` (with UTF-8 env)
    ```text
    SUCCESS: Unit: 23 tests
    SUCCESS: Integration: 2 tests
    Unit Tests:        PASS
    Integration Tests: PASS
    Agentic Tests:     WARN
    [INVARIANTS]
    UNIT_TESTS=PASS
    INTEGRATION_TESTS=PASS
    AGENTIC_TESTS=WARN
    ```
  - Notes: Validates persistence across instance restarts (write -> restart -> read).

- **Memory Persistence (SQLite via Factory)**
  - State: Verified
  - Location: `backend/memory/stores/sqlite_store.py`, `backend/memory/factory.py`, `backend/core/config/settings.py`, `tests/integration/test_workflow_persistence.py`
  - Validation: `backend/.venv/Scripts/python.exe -m pytest tests/integration -q`
    ```text
    ...                                                                      [100%]
    3 passed in 0.13s
    ```
  - Validation: `backend/.venv/Scripts/python.exe scripts/validate_backend.py`
    ```text
    SUCCESS: Integration: 3 tests
    Integration Tests: PASS
    ```

- **Tier 1 Working State Manager (Ephemeral)**
  - State: Verified
  - Location: `backend/memory/working_state.py`, `tests/unit/test_working_state.py`
  - Validation: `backend/.venv/Scripts/python.exe -m pytest tests/unit/test_working_state.py -q`
    ```text
    ........                                                                                     [100%]
    8 passed in 0.26s
    ```
  - Validation: `backend/.venv/Scripts/python.exe scripts/validate_backend.py`
    ```text
    SUCCESS: Unit: 31 tests
    SUCCESS: Integration: 3 tests
    ✅ JARVISv4 Backend is FULLY validated!
    ```
  - Notes: Implements ECF Tier 1 memory using JSON for ephemeral task state tracking with atomic writes and schema validation.

- **Planner Agent**
  - State: Verified
  - Location: `backend/agents/planner/planner.py`, `tests/unit/test_planner.py`
  - Validation: `backend/.venv/Scripts/python.exe -m pytest tests/unit/test_planner.py -q`
    ```text
    .....                                                                    [100%]
    5 passed in 1.54s
    ```
  - Validation: `python scripts/verify_planner_integration.py`
    ```text
    ✅ Task file created.
    ✅ Data validation PASSED.
    ```
  - Notes: Stateless reasoning component integrated with `OpenAIProvider`. Verified to produce valid DAG task files in `tasks/`.

- **LLM Provider Service**
  - State: Verified
  - Location: `backend/core/llm/`, `scripts/test_llm_connectivity.py`
  - Validation: `pytest tests/unit/test_llm_provider.py` (5/5 PASS)
  - Validation: `python scripts/test_llm_connectivity.py` (Smoke Test)
    ```text
    INFO:__main__:✅ SMOKE TEST PASSED: Handshake verified.
    ```
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
    ```text
    ✅ SMOKE TEST PASSED
    ```
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
    ```text
    INFO: Mined Episode 1: Input='Explain what 2+2 is', Expected='2+2 is 4'
    INFO: JUDGE PROMPT: Goal: Explain what 2+2 is [...]
    INFO: JUDGE RESPONSE: YES
    2 passed in 8.16s
    ```
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
    ```text
    ✓ PASS: tests.integration.test_learning_cycle::test_full_learning_cycle
    SUCCESS: Integration: 5 tests
    ```
  - Notes: End-to-end proof of ECF Learning Loop: Task Execution (Trace Generation) -> Episode Curation (Data Extraction) -> Dataset Mixing (Blend with Basal) -> Training Orchestration (Dry Run).

- **Privacy Engine (Port)**
  - State: Verified (Audit Date: 2026-01-21)
  - Location: `backend/core/privacy.py`, `tests/unit/test_privacy.py`
  - Validation: `.\backend\.venv\scripts\python scripts/validate_backend.py`
    ```text
    ✓ PASS: tests.unit.test_privacy::test_privacy_encryption_roundtrip
    ✓ PASS: tests.unit.test_privacy::test_privacy_classification
    ✓ PASS: tests.unit.test_privacy::test_privacy_redaction_partial
    ✓ PASS: tests.unit.test_privacy::test_privacy_redaction_strict
    ✓ PASS: tests.unit.test_privacy::test_privacy_audit_log
    ✓ PASS: tests.unit.test_privacy::test_privacy_hash_id
    ```
  - Notes: Consolidated v2 Encryption (AES-GCM/PBKDF2) and v3 Compliance (Classification/Redaction/Audit). Replaced `pycryptodome` with `cryptography` library.

- **Semantic Memory (Tier 3)**
  - State: Verified (Audit Date: 2026-01-21)
  - Location: `backend/memory/stores/semantic.py`, `tests/unit/test_semantic_memory.py`
  - Validation: `.\backend\.venv\scripts\python scripts/validate_backend.py`
    ```text
    ✓ PASS: tests.unit.test_semantic_memory::test_semantic_memory_init
    ✓ PASS: tests.unit.test_semantic_memory::test_add_pattern
    ✓ PASS: tests.unit.test_semantic_memory::test_retrieve_similar
    ✓ PASS: tests.unit.test_semantic_memory::test_retrieve_with_domain_filter
    ✓ PASS: tests.unit.test_semantic_memory::test_persistence
    ✓ PASS: tests.unit.test_semantic_memory::test_guardrails
    ```
  - Notes: Implements ECF Tier 3 hybrid memory using Scikit-Learn (vector similarity) and SQLite (symbolic metadata). Optimized for clean, warning-free execution on Python 3.12.

- **Budget Service (Safety Limits)**
  - State: Verified (Audit Date: 2026-01-21)
  - Location: `backend/core/budget.py`, `backend/core/config/settings.py`
  - Validation: `backend/.venv/Scripts/python.exe -m pytest tests/unit/test_budget.py`
    ```text
    tests\unit\test_budget.py ........                                                                 [100%]
    8 passed in 0.13s
    ```
  - Notes: Ports v2 Budget Service for granular cost tracking and enforcement. Uses SQLite for persistence with daily reset logic. Supports 'none', 'log', and 'block' enforcement levels.
