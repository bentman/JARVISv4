# CHANGE_LOG.md

## Instructions

- Append-only history of completed, validated work.
- Write an entry only after the mini-phase objective is “done” and supported by evidence.
- No edits/reorders/deletes of past entries. If an entry is wrong, append a corrective entry.
- Each entry must include:
  - Timestamp: `YYYY-MM-DD HH:MM`
  - Summary: 1–2 lines, past tense
  - Scope: files/areas touched
  - Evidence: exact command(s) run + a minimal excerpt pointer (or embedded excerpt ≤10 lines)
- If a change is reverted, append a new entry describing the revert and why.

## Entries

- 2026-01-17 00:00
  - Summary: Initialized governance scaffolding files (AGENTS.md, CHANGE_LOG.md, SYSTEM_INVENTORY.md) and Cline rule set under .clinerules/.
  - Scope: AGENTS.md; CHANGE_LOG.md; SYSTEM_INVENTORY.md; .clinerules/00-guardrails.md; .clinerules/10-mini-phase.md; .clinerules/20-validation-tests.md; .clinerules/30-doc-truth.md; .clinerules/40-inventory-states.md; .clinerules/50-change-log.md
  - Evidence: Manual file creation (no command-run evidence recorded).

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
