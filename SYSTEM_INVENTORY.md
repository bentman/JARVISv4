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
