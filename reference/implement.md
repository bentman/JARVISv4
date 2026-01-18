# This document is reference-only planning notes. 
# Not authoritative. Reference only if specifically instructed.
# Terminology may lag core docs; follow `..\Project.md` + `..\AGENTS.md`

# reference\IMPLEMENT.md
Artifact-Driven, Local-First Agent System — Implementation Plan Baseline (No Timelines)

> **Goal**
> Build a local-first assistant as a **deterministic system** where the model is a **stateless reasoning component**.
> State, memory, validation, and improvement live in **versioned artifacts**, **tool transcripts**, and **gated learning loops**.

---

## 0) Non-Negotiable Invariants

### Invariants
- [ ] The model is treated as **stateless** (no prompt-as-memory).
- [ ] Orchestration is owned by a **deterministic controller** (FSM/DAG).
- [ ] Memory is externalized into artifacts with clear layers: **working**, **episodic**, **semantic**.
- [ ] “Learning” is **explicit** and must land as one of:
  - [ ] Controller / validator / policy changes (code + tests), **or**
  - [ ] Versioned weight updates (LoRA/QLoRA adapters), **or**
  - [ ] Tooling/contract improvements (schemas, executors, sandboxing)
- [ ] All improvements are **regression-gated** and **rollbackable**.
- [ ] Every tool action is attributable to a persisted transcript (params + outputs + exit codes).
- [ ] Every output can be audited end-to-end without relying on model narrative.

### Definition of done
- [ ] For any result, we can trace: `task → plan → decisions → tool transcripts → eval → results` with file pointers.
- [ ] Replaying the same episode reproduces the same artifacts and tool calls (or pinpoints the nondeterministic boundary).
- [ ] No critical behavior depends on unversioned prompts or hidden state.

---

## 1) Repository Layout (Authoritative)

### Target structure
```text
repo/
  IMPLEMENT.md
  README.md
  docs/
    architecture.md
    schemas.md
    runbooks/
      replay.md
      adapter_promotion.md
      incident_response.md
  controller/
    engine/              # FSM/DAG engine + transition logic
    nodes/               # atomic node implementations
    policies/            # context injection, retry, budget, safety
    validators/          # deterministic + semantic validators
  agents/
    planner/             # writes plan.yaml
    executor/            # executes one step
    critic/              # validates + writes eval.json
    curator/             # extracts dataset examples
    trainer/             # runs fine-tune jobs (local)
  artifacts/
    templates/           # canonical templates for task/plan/eval/logs
    schemas/             # JSON Schema / Pydantic models
  memory/
    episodic/            # immutable logs/transcripts/episode index
    semantic/            # curated rules + distilled knowledge
  tools/
    registry/            # tool definitions + schemas
    executors/           # sandbox runners + adapters
    transcripts/         # raw append-only transcripts
  eval/
    suites/              # regression tasks + gold outputs
    metrics/             # drift metrics + reporting
  datasets/
    extracted/           # raw extracted examples
    curated/             # filtered/approved training sets
  adapters/
    registry/            # adapter metadata + hashes + promotion state
    builds/              # produced adapter files (ignored if large)
  scripts/
  tests/
```

### Checklist
- [ ] One “source of truth” for schemas and artifact contracts exists under `artifacts/schemas/`.
- [ ] All persistent artifacts are versioned by content hash and/or git commit.
- [ ] `tools/transcripts/` is immutable/append-only (write once).

### Definition of done
- [ ] A new contributor can locate: artifacts, controller, validators, datasets, adapters, and replay entrypoints quickly.
- [ ] Every directory has a short README (or doc link) describing purpose and contracts.

---

## 2) Core Concepts & Glossary (Keep Tight)

### Episode
An **episode** is one full unit of work consisting of:
- task specification
- plan
- decisions
- tool transcripts
- evaluation report
- resulting diffs/outputs

### Memory Layers
- **Working state (ephemeral):** minimal state needed for the current node/step
- **Episodic trace (immutable):** complete transcripts + decision logs + outcomes
- **Semantic memory (curated):** distilled rules/patterns/preferences, versioned

### Definition of done
- [ ] These definitions are reflected in code (types), docs, and storage layout.

---

## 3) Artifact Model (Schemas + Templates)

### Required artifacts (minimum)
- `task.yaml` — goal, constraints, acceptance checks, current-step pointer, budgets
- `plan.yaml` — nodes/steps, dependencies, invariants, tool permissions
- `decision_log.jsonl` — append-only decisions (what/why) with evidence pointers
- `tool_transcripts/*.jsonl` — raw tool I/O (params, stdout/stderr, exit codes)
- `eval.json` — pass/fail, metrics, reasons, validator outputs
- `results/` — outputs + diffs (prefer patch files + final artifacts)

### Checklist
- [ ] Define **schemas** for every artifact (JSON Schema or Pydantic).
- [ ] Provide canonical templates in `artifacts/templates/`.
- [ ] Enforce schema validation at:
  - [ ] write-time (artifact creation)
  - [ ] read-time (artifact loading)
  - [ ] transition-time (before controller advances state)

### Definition of done
- [ ] Invalid artifacts fail fast with actionable errors.
- [ ] Artifacts remain human-readable and git-friendly.
- [ ] A complete episode can be reconstructed solely from persisted artifacts.

---

## 4) Deterministic Controller (FSM/DAG)

### Controller responsibilities
- context selection/injection policy (strict + minimal)
- role routing (planner/executor/critic/curator/trainer)
- retry/rollback policies
- budget enforcement (tokens/tool calls/time)
- hard stop conditions + safe failure modes
- episode persistence (indexes + pointers)

### Controller execution model (recommended)
Represent workflow as atomic nodes, e.g.:
- `INIT → PLAN → EXECUTE_STEP → VALIDATE → COMMIT → (NEXT_STEP | REPLAN | FAIL_CLOSED)`

### Checklist
- [ ] Implement a minimal FSM/DAG engine with explicit transitions.
- [ ] All transitions require:
  - [ ] schema-valid inputs
  - [ ] deterministic predicate outcomes (validator outputs)
  - [ ] persisted state updates

### Definition of done
- [ ] Deterministic replay is possible from an episode root.
- [ ] Controller never depends on unpersisted model “memory”.

---

## 5) Role-Separated Micro-Agents (Strict Contracts)

### Roles and allowed outputs
- **Planner**
  - Input: `task.yaml` + relevant semantic memory
  - Output: `plan.yaml` only
- **Executor**
  - Input: current node + tool permissions + relevant artifacts
  - Output: tool transcripts + result diffs/artifacts (one step only)
- **Critic / Validator**
  - Input: transcripts + diffs + acceptance checks
  - Output: `eval.json` + structured feedback
- **Curator**
  - Input: validated episodes + failure clusters
  - Output: dataset rows (JSONL) with labels/metadata
- **Trainer**
  - Input: curated dataset + training config
  - Output: versioned adapter + regression report + promotion request

### Checklist
- [ ] Define input/output schemas for each role.
- [ ] Enforce “no cross-role mutation” (e.g., executor cannot rewrite plan).
- [ ] Handoffs occur only via persisted artifacts (no hidden chat).

### Definition of done
- [ ] Each role can be unit-tested in isolation with fixture artifacts.
- [ ] Role outputs are rejectable by schema/validators without human interpretation.

---

## 6) Tools: Deterministic Execution, Transcripts, and Sandboxing

### Tool executor requirements
- pre-validate tool params (schema)
- sandbox execution (filesystem/network/process)
- timeouts + resource limits
- post-validate outputs (schema)
- persist transcript (params, stdout/stderr, exit codes, hashes)

### Checklist
- [ ] Tool registry includes:
  - [ ] name, description
  - [ ] param schema
  - [ ] output schema
  - [ ] safety classification (read-only / write / destructive)
- [ ] Transcript writer is append-only; redaction runs before persistence.

### Definition of done
- [ ] No tool action occurs without a stored transcript entry.
- [ ] Any tool failure is visible in eval and blocks unsafe continuation by default.

---

## 7) Context Injection Policy (Anti-Collapse Guardrail)

### Principles
- minimal necessary context per node
- artifacts are primary; semantic memory is curated; episodic recall is narrow
- never inject full history by default
- pin critical decisions via explicit pointers (decision log IDs)

### Checklist
- [ ] Implement context builder that:
  - [ ] selects artifact slices deterministically
  - [ ] includes only the node contract inputs
  - [ ] adds “do not invent state” instruction tokens (short, consistent)
- [ ] Log every context bundle: what was included and why.

### Definition of done
- [ ] Context bundles are reproducible, inspectable, and minimal.
- [ ] Increasing task complexity does not linearly grow prompt size.

---

## 8) Validators & Acceptance Checks (Fail Closed)

### Validator types
- **Deterministic validators** (preferred)
  - schema checks, diff checks, file existence, exit codes, unit tests, lint, policy rules
- **Semantic validators** (supplemental)
  - model-assisted consistency checks, contradiction detection, rationale sanity checks

### Checklist
- [ ] Every node has explicit acceptance checks.
- [ ] “Semantic” checks cannot override deterministic failures.
- [ ] Validator outputs are written to `eval.json` in a machine-readable format.

### Definition of done
- [ ] Unsafe or unverified actions are blocked by default.
- [ ] All “pass” decisions are defensible from artifact evidence.

---

## 9) Observability, Replay, and Drift Detection

### What to log (minimum)
- LLM call metadata: template ID, inputs (artifact refs), outputs, tokens, latency
- State transitions: from→to, node ID, retry count, reasons
- Tool calls: transcript pointers, exit codes, output hashes
- Eval outcomes: pass/fail, validators fired, metrics

### Drift metrics (minimum set)
- behavioral variance (repeat task stability)
- regression rate (solved tasks failing)
- context efficiency (work per token)
- validation failure rate (hallucination/tool mismatch indicators)

### Checklist
- [ ] Implement episode index with search/filter.
- [ ] Implement a single replay command to reconstruct an episode deterministically.
- [ ] Store metric snapshots per episode.

### Definition of done
- [ ] You can answer: “when did behavior change?” using metrics + adapter/controller diffs.
- [ ] A regression is reproducible from a specific episode ID.

---

## 10) Evaluation Harness (Regression Suite + Gold Episodes)

### Regression suite
- curated set of solved tasks (episodes) with gold outputs and acceptance rules
- must run on:
  - controller changes
  - validator changes
  - adapter promotion requests

### Checklist
- [ ] Add `eval/suites/` with:
  - [ ] task definitions
  - [ ] gold artifacts / expected diffs
  - [ ] run scripts
- [ ] Add “retention threshold” gate and report format.

### Definition of done
- [ ] Any change that regresses the suite is blocked (or requires explicit override artifact).
- [ ] Regression reports include: failing episodes, diffs, metrics deltas, suspected root causes.

---

## 11) Explicit Learning Loop (Experience → Dataset → Adapter), Gated

### Pipeline (authoritative)
1. Capture episodes (task + artifacts + transcripts + eval)
2. Select high-quality episodes (passed tests; low-risk)
3. Extract training tuples (JSONL) with consistent structure
4. Filter & label (redaction, metadata, failure modes)
5. Train (LoRA/QLoRA) producing versioned adapter
6. Gate with regression suite + drift checks
7. Deploy versioned adapter with rollback
8. Monitor and iterate

### Dataset contracts (minimum)
Each example includes:
- `input`: artifact slice + node contract context (not full history)
- `target`: desired next action/output (plan node, patch, tool call plan, etc.)
- `labels`: domain/tools/failure_mode/risk_level
- `provenance`: episode ID + transcript pointers + eval proof

### Checklist
- [ ] Implement curator that can:
  - [ ] mine episodes by label/failure cluster
  - [ ] generate JSONL examples deterministically
  - [ ] enforce redaction and schema checks
- [ ] Training runs produce:
  - [ ] adapter hash
  - [ ] training config snapshot
  - [ ] dataset hash
  - [ ] evaluation report

### Definition of done
- [ ] No adapter is promoted without a dataset hash + config hash + passing regression report.
- [ ] Every promoted adapter is rollbackable and tied to provenance.

---

## 12) Adapter Registry, Promotion, and Rollback

### Adapter registry fields (minimum)
- adapter ID + hash
- base model reference
- dataset hash + selection policy
- training config hash
- regression report pointer
- promotion state (candidate/canary/stable/retired)
- rollback notes

### Checklist
- [ ] Implement `adapters/registry/` as machine-readable metadata (JSON/YAML).
- [ ] Add canary routing policy (subset of tasks/domains) before stable promotion.
- [ ] Enforce “one command rollback” to a previous stable adapter.

### Definition of done
- [ ] You can answer: “what changed in behavior and why?” via registry + eval diffs.
- [ ] Rollback restores prior regression suite performance.

---

## 13) Security & Safety (Local-First, Human-Controlled)

### Defaults
- least-privilege tool permissions
- read-only mode available globally
- explicit approval artifact for destructive actions
- secret/PII redaction before persistence and before dataset extraction

### Checklist
- [ ] Tool registry marks destructive tools; controller blocks them unless approved.
- [ ] Redaction pipeline is tested.
- [ ] Dataset export requires a signed approval step (artifact-backed).

### Definition of done
- [ ] No secrets/PII enter datasets or logs unredacted.
- [ ] Destructive actions cannot occur without explicit approvals and transcripts.

---

## 14) Operator UX (Auditability First)

### Must-have operator features
- episode browser (task, plan, decisions, transcripts, eval, results)
- replay trigger + replay diff view
- adapter pin/rollback controls
- strictness toggles (read-only vs write-enabled)
- “approval required” workflow for destructive operations

### Checklist
- [ ] Provide a local UI or CLI with clear commands and outputs.
- [ ] Every UI action results in artifacts/logs (no hidden state).

### Definition of done
- [ ] A user can audit any result end-to-end without interpreting model prose.
- [ ] A user can reproduce a result (or failure) from the episode ID.

---

## 15) Implementation Sequencing (No Timelines)

> Build in dependency order to avoid rewrites.

### Dependency order
- [ ] Artifacts + schemas + templates + ledger
- [ ] Controller foundation (FSM/DAG + transitions)
- [ ] Tool executor + transcripts (sandbox + validation)
- [ ] Micro-agent role shells (contracts + unit tests)
- [ ] Observability + replay
- [ ] Validators + regression suite + drift metrics
- [ ] Curator + datasets + training harness (Unsloth) + adapter registry
- [ ] Operator UI + packaging

### Definition of done
- [ ] Each layer is usable before the next is added (vertical slices).
- [ ] No learning loop is enabled before regression gates exist.

---

## 16) “First Working Slice” (Minimal Viable End-to-End)

### Slice scope (minimum)
- one task type
- one planner step
- one executor tool
- one deterministic validator
- full episode persistence + replay

### Checklist
- [ ] `task.yaml` → `plan.yaml` generation works.
- [ ] One `EXECUTE_STEP` produces a transcript + result diff.
- [ ] `eval.json` gates state transition.
- [ ] Episode is replayable.

### Definition of done
- [ ] You have a complete audit trail for a single solved task.
- [ ] You can replay the episode and reproduce the same outputs.

---

## Appendix A) Canonical Templates (Placeholders)

### `artifacts/templates/task.yaml`
```yaml
id: ""
title: ""
goal: ""
constraints:
  - ""
acceptance:
  - id: ""
    description: ""
    type: ""   # e.g. test, file_exists, diff_match, lint_pass
    params: {}
budgets:
  max_steps: 0
  max_tool_calls: 0
  max_tokens: 0
state:
  current_node: ""
  status: ""  # new|in_progress|blocked|done|failed
```

### `artifacts/templates/plan.yaml`
```yaml
id: ""
task_id: ""
invariants:
  - ""
nodes:
  - id: "PLAN"
    type: "planner"
    deps: []
  - id: "STEP_001"
    type: "executor"
    deps: ["PLAN"]
    tool_permissions: ["read_only_tools"]
  - id: "VALIDATE_001"
    type: "critic"
    deps: ["STEP_001"]
transitions:
  - from: "PLAN"
    to: "STEP_001"
    when: "plan_valid"
  - from: "STEP_001"
    to: "VALIDATE_001"
    when: "tool_success"
  - from: "VALIDATE_001"
    to: "DONE"
    when: "acceptance_pass"
fallbacks:
  - from: "VALIDATE_001"
    to: "REPLAN"
    when: "acceptance_fail"
```

### `artifacts/templates/eval.json`
```json
{
  "task_id": "",
  "episode_id": "",
  "node_id": "",
  "status": "pass",
  "metrics": {
    "token_count": 0,
    "tool_calls": 0,
    "context_bytes": 0,
    "validation_failures": 0
  },
  "validators": [
    {
      "id": "",
      "type": "deterministic",
      "status": "pass",
      "details": {}
    }
  ],
  "notes": ""
}
```

### `artifacts/templates/decision_log.jsonl`
```jsonl
{"ts":"","episode_id":"","node_id":"","decision":"","why":"","evidence":["artifact://...","transcript://..."],"hash":""}
```

---

## Appendix B) Commands (Document in docs/runbooks/)

### Replay (placeholder)
- `scripts/replay_episode.py --episode <ID> --mode deterministic`

### Run regression suite (placeholder)
- `scripts/run_regression.py --suite core --adapter <ID-or-none>`

### Extract dataset (placeholder)
- `scripts/extract_dataset.py --from episodes --label <...> --out datasets/extracted/...`

### Train adapter (placeholder)
- `scripts/train_adapter.py --dataset <hash> --out adapters/builds/...`

---

## Appendix C) Contribution Rules (Guardrails)

- [ ] Do not expand prompt context to “fix” memory; add/adjust artifacts and retrieval policies instead.
- [ ] Do not merge roles; keep contracts strict.
- [ ] Do not promote adapters without passing regression gates.
- [ ] Prefer deterministic validators over model-based critique.

