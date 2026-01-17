# AGENTS.md — JARVISv4 Agent Working Agreement (Canonical)

This file is the single authoritative instruction set for agents and contributors working in this repository.

## 1 Operating constraints (always)

- No guessing. If something can’t be verified from the repo, state what was checked and stop for direction.
- No completion claims without reproducible evidence (command(s) run + minimal excerpt).
- One objective per mini-phase. No scope expansion. Adjacent work becomes a new mini-phase.
- No new repo artifacts unless explicitly requested.
- Prefer existing repo patterns; avoid parallel architectures or “shadow systems”.
- Keep outputs small: only lines needed to prove a claim; no large log pastes unless diagnosing failure.

## 2 Precedence and truth sources (use in this order)

1) `AGENTS.md` (this file)
2) `Project.md` (repo intent and required structure)
3) `SYSTEM_INVENTORY.md` (what is true now; evidence-gated)
4) `CHANGE_LOG.md` (append-only history of completed work with evidence)

If these conflict with observed repo behavior, report the conflict and propose the smallest correction.

## 3 Legacy references (read-only, non-authoritative)

- `reference/JARVISv2_ref/`
- `reference/JARVISv3_ref/`

Purpose: historical reference for porting/comparisons only. Do not treat legacy docs or legacy conventions as instructions for v4 unless explicitly stated in v4 files.

## 4 Repo layout anchors (v4)

Follow `Project.md` Section 2 for the repo tree. Key anchors:
- Backend entrypoint: `backend/main.py`
- Backend validation harness: `scripts/validate_backend.py`
- Backend tests: `tests/unit/`, `tests/integration/`, `tests/agentic/`
- Backend structure:
  - `backend/core/{config,observability,hardware}/`
  - `backend/controller/{engine,nodes}/`
  - `backend/agents/{planner,executor}/`
  - `backend/memory/{stores,schemas}/`
  - `backend/tools/{registry,sandbox}/`
  - `backend/artifacts/`, `backend/datasets/`
- Frontend:
  - `frontend/` is the UI workspace
  - `frontend/Dockerfile` is the container build definition for the UI
  - Keep frontend changes isolated to `frontend/` unless explicitly approved otherwise

## 5 Python environment isolation (high priority)

- All Python execution for this repo uses the project venv at `backend/.venv`.
- Do not use or modify the User’s global Python environment.
- Do not install packages globally. No `pip install` outside `backend/.venv`.
- Dependency source of truth is `backend/requirements.txt`.
  - Any dependency change must update `backend/requirements.txt` in the same mini-phase (or stop at proposal-only first if risk is non-trivial).
- If `backend/.venv` does not exist or is broken, stop and propose the minimal create/repair steps before proceeding.

## 6 Default workflow (mini-phase, evidence-gated)

Per mini-phase:
- One objective.
- Discovery first (identify smallest file set + authoritative commands).
- If risk is non-trivial, stop at proposal-only (Section 7).
- Implement only what was approved.
- Validate with the smallest relevant check first; expand only after it passes.
- Stop immediately after the objective is met and validated with evidence.

Failure loop rule:
- If attempts repeat without changing the failure mode, stop and propose a different strategy.

## 7 Proposal-only mode (approval gate)

Before editing, enter proposal-only mode when work touches any of:
- Multiple files
- Core backend subsystems (`backend/core`, `controller`, `agents`, `memory`, `tools`)
- Tests or validation harnesses
- Docker/compose surfaces
- Frontend build/runtime surfaces
- Build/deploy/CI-like flows
- Dependency changes (`backend/requirements.txt`) or venv creation/repair (`backend/.venv`)

Proposal must include:
- Exact files to touch (and why)
- Minimal validation command(s)
- Expected evidence excerpt(s)
Then stop.

## 8 Validation rules (backend + frontend)

General:
- Prefer existing harnesses and tests; do not invent new validators unless explicitly requested.
- Warnings are backlog, not blockers, unless they break correctness or user-visible behavior.
- Host vs Docker truth separation: do not force host parity with container behavior unless explicitly requested.
- When reporting pass/fail, include the exact command and a minimal excerpt showing the result.

Backend:
- Run Python commands via `backend/.venv` (Section 5).
- Primary harness: `scripts/validate_backend.py`
- Tests live under `tests/` and should be runnable selectively (single file/case first).

Frontend:
- Changes must be validated using the smallest relevant frontend check (project-defined command(s)).
- If frontend validation depends on container behavior, validate via the frontend container surface (`frontend/Dockerfile` / compose), not by inventing host-only workarounds.

## 9 Documentation and logging (ordering + standards)

Documentation updates happen only after validation evidence supports the claim.

### 9.1 CHANGE_LOG.md (append-only) — required format

- Append-only. Do not rewrite history.
- Log only after the objective is validated “done” with evidence.
- If a prior entry is wrong, append a corrective entry; do not edit old entries.

Entry template (single change):
- Timestamp: `YYYY-MM-DD HH:MM`
- Summary: 1–2 lines, past tense
- Scope: files/areas touched
- Evidence: command(s) + minimal excerpt pointer (or embedded excerpt ≤10 lines)

### 9.2 SYSTEM_INVENTORY.md — standards

- `SYSTEM_INVENTORY.md` is a status snapshot, not a promise.
- Promote a capability/state only when supported by validation evidence.
- Keep entries terse: what exists, where it lives, how it was validated.
- Add new entries; do not rewrite history.
- Corrections are appended with date + evidence pointer.

## 10 Git safety

Never run destructive git commands without explicit approval:
- `git restore`, `git reset`, `git clean`, `git rebase`, history rewrites

If rollback is requested, propose the safest approach based on whether changes are committed or uncommitted.

## 11 Reporting format (agent output)

- Summary (1–3 sentences)
- Files inspected and/or touched
- Commands executed + outcomes
- Evidence excerpt(s) (max 10 lines per item)
- Next step proposal (scoped), or stop if complete
