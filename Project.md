# Project.md: Local-First Explicit Cognition Framework (ECF)

> **Source of Truth**
> This document is the authoritative project plan for the Local-First Agent System. It synthesizes the architectural principles of the Explicit Cognition Framework (ECF) with a concrete implementation strategy.

---

## 1. Project Vision

To build a **local-first, artifact-driven AI assistant** where the LLM is a **stateless reasoning component**. The system relies on externalized memory, deterministic control structures, and explicit learning loops to prevent drift and ensure reliability.

### Core Invariants
1.  **Stateless Reasoning:** The model never retains state between calls.
2.  **Externalized Memory:** All context is retrieved from structured artifacts (Working, Episodic, Semantic).
3.  **Deterministic Control:** A Finite State Machine (FSM) or DAG governs execution flow, not the model.
4.  **Explicit Learning:** Improvement comes from fine-tuning weights, not accumulating prompts.
5.  **Local-First:** Full offline capability on consumer hardware.

---

## 2. Repository Architecture

The project follows a strict directory structure to enforce separation of concerns.

```text
repo/
├── Project.md                  # This file (Source of Truth)
├── AGENTS.md                   # Ruling document for Agent behavior
├── README.md                   # Quickstart & Usage
├── docs/                       # Documentation
│   ├── architecture/           # ECF Technical Specs (from ecf_*.md)
│   └── runbooks/               # Operational guides (replay, train, deploy)
├── controller/                 # Deterministic Orchestration
│   ├── engine/                 # FSM/DAG execution logic
│   ├── nodes/                  # Atomic workflow steps
│   └── validators/             # Deterministic & Semantic validators
├── agents/                     # Micro-Agent Implementations
│   ├── planner/                # Task decomposition
│   ├── executor/               # Tool execution
│   ├── critic/                 # Output validation
│   ├── curator/                # Dataset mining
│   └── learner/                # Training orchestration
├── memory/                     # Memory System
│   ├── working/                # Ephemeral task state (YAML)
│   ├── episodic/               # Immutable decision logs (SQLite)
│   └── semantic/               # Knowledge patterns (FAISS + SQLite)
├── tools/                      # Deterministic Tooling
│   ├── registry/               # Tool definitions & schemas
│   └── sandbox/                # Execution environment
├── artifacts/                  # Data Schemas & Templates
│   ├── schemas/                # Pydantic/JSON Schemas
│   └── templates/              # Canonical artifact templates
├── datasets/                   # Learning Data
│   ├── extracted/              # Raw mined examples
│   └── curated/                # Training-ready datasets
└── adapters/                   # Model Weights
    ├── registry/               # Adapter metadata
    └── storage/                # LoRA/QLoRA files
```

---

## 3. System Specifications

### 3.1 Memory System (The "Brain")
*Reference: `reference/ecf_part2_memory.md`*

The memory system replaces the context window as the source of truth.

*   **Tier 1: Working State (Ephemeral)**
    *   **Storage:** YAML files on disk.
    *   **Schema:** `task_id`, `goal`, `status`, `current_step`, `completed_steps`, `next_steps`.
    *   **Lifecycle:** Created at task start, archived upon completion.
*   **Tier 2: Episodic Trace (Immutable)**
    *   **Storage:** SQLite (`decisions`, `tool_calls`, `validations` tables).
    *   **Function:** Append-only log of every action, input, output, and outcome.
    *   **Key Feature:** Enables deterministic replay of any episode.
*   **Tier 3: Semantic Memory (Curated)**
    *   **Storage:** SQLite (`patterns`, `guardrails`) + FAISS (Vector Index).
    *   **Function:** Stores validated patterns and user preferences.
    *   **Retrieval:** Hybrid search (Semantic similarity + Symbolic filtering).

### 3.2 Deterministic Controller (The "Spine")
*Reference: `reference/ecf_part1_overview.md`*

Control flow is hard-coded in Python/Rust, not hallucinated by the LLM.

*   **Mechanism:** State Machine / DAG.
*   **Flow:** `INIT` → `PLAN` → `EXECUTE` → `VALIDATE` → `COMMIT` → `NEXT`.
*   **Context Injection:** Minimal context slices based on current node requirements.
*   **Validation:** "Fail Closed" policy. Invalid outputs trigger retries or failure, never silent corruption.

### 3.3 Micro-Agents (The "Hands")
*Reference: `reference/ecf_part3_agents.md`*

Monolithic agents are decomposed into specialized roles.

| Role | Responsibility | Input | Output |
| :--- | :--- | :--- | :--- |
| **Planner** | Strategy & Decomposition | Goal + Constraints | `plan.yaml` (DAG) |
| **Executor** | Tool Invocation | Task Step + Context | Tool Result + Artifacts |
| **Critic** | Validation | Result + Requirements | `eval.json` (Pass/Fail) |
| **Curator** | Data Mining | Execution Logs | Training Examples (JSONL) |
| **Learner** | Fine-Tuning | Curated Dataset | New Adapter Version |

### 3.4 Learning Pipeline (The "Growth")
*Reference: `reference/ecf_part4_learning.md`*

Improvement is explicit and weight-based.

1.  **Capture:** Log every episode.
2.  **Filter:** Select high-quality, successful episodes (Multi-gate: Outcome, Security, Quality Score).
3.  **Extract:** Convert to Instruction-Input-Output tuples.
4.  **Mix:** Blend with Basal Dataset (70% Curriculum / 30% Basal) to prevent catastrophic forgetting.
5.  **Train:** Unsloth Fine-tuning (LoRA/QLoRA).
6.  **Gate:** Run Regression Suite.
7.  **Deploy:** Versioned Adapter Rollout.

---

## 4. Implementation Plan

### Phase 1: Foundation (Weeks 1-4)
**Goal:** Functional Controller & Memory System.
- [ ] **Repo Setup:** Directory structure, Docker environment.
- [ ] **Memory:** Implement `WorkingStateManager`, `EpisodicMemory` (SQLite), `SemanticMemory` (FAISS).
- [ ] **Controller:** Implement base FSM engine and Context Builder.
- [ ] **Artifacts:** Define `task.yaml`, `plan.yaml`, `decision_log.json` schemas.
- [ ] **Validation:** System can execute a linear "Hello World" workflow deterministically.

### Phase 2: Agents & Tools (Weeks 5-8)
**Goal:** Specialized Roles & Deterministic Execution.
- [ ] **Agents:** Implement `Planner`, `Executor`, `Critic` shells and prompts.
- [ ] **Tools:** Build Sandbox Executor and Tool Registry.
- [ ] **Communication:** Implement structured message passing (no conversational loops).
- [ ] **Validation:** System can plan and execute a multi-step task with tool calls.

### Phase 3: Learning Loop (Weeks 9-12)
**Goal:** Self-Improvement Pipeline.
- [ ] **Curator:** Implement `EpisodeCapture` and `QualityFilter`.
- [ ] **Learner:** Set up Unsloth training pipeline.
- [ ] **Regression:** Build `RegressionSuite` and `BasalDatasetManager`.
- [ ] **Validation:** Complete one full cycle: Task → Log → Dataset → Adapter → Deployed Improvement.

### Phase 4: Production & Operations (Weeks 13-16)
**Goal:** Deployment & Observability.
- [ ] **Ops:** Docker Compose stack (Controller, vLLM, VectorDB, Grafana).
- [ ] **UI:** Operator Control Panel (Task submission, History, Replay).
- [ ] **Monitoring:** Drift detection, Latency metrics, Hallucination alerts.
- [ ] **Validation:** System runs stable for 7+ days with <5% drift.

---

## 5. Success Metrics

| Metric | Target | Definition |
| :--- | :--- | :--- |
| **Reproducibility** | 100% | Replaying an episode produces identical artifacts. |
| **Memory Recall** | >95% | Accuracy of retrieving relevant past decisions. |
| **Task Success** | >85% | Tasks completed without human intervention. |
| **Drift Rate** | <5% | Behavioral variance over 30 days. |
| **Regression** | >95% | Pass rate on historical test suite after updates. |
| **Latency** | <200ms | P95 Controller overhead (excluding inference). |
