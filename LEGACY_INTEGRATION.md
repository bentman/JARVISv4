# JARVISv4: Legacy Integration & Porting Strategy

## 1. Executive Summary
JARVISv4 (Codename: `JARVISv4`) is the successor to JARVISv2 and JARVISv3. This document outlines the strategy for leveraging the high-maturity codebases of its predecessors to accelerate the implementation of the **Explicit Cognition Framework (ECF)**.

**Key Objective:** Leverage approximately 80% of legacy infrastructure and core services while refactoring the remaining 20% to enforce stateless reasoning and artifact-driven memory.

**Reference Policy:**
All legacy code resides in the `./reference/` directory. These paths are intentionally **read-only** and serve as the source for porting logic into the JARVISv4 codebase.
*   **JARVISv2 Source:** `./reference/JARVISv2_ref`
*   **JARVISv3 Source:** `./reference/JARVISv3_ref`

---

## 2. Conceptual Evolution & Strategic Shifts

### 2.1 The "Spine" vs. The "Driver"
*   **Conflict (v2/v3):** In earlier versions, the LLM often acted as the primary driver of the conversation or task, leading to unpredictable loops and "hallucinated" state management.
*   **Resolution (v4):** The LLM is demoted to a **Stateless Reasoning Component**. The **Deterministic Controller** (ported and enhanced from v3) is the authoritative "spine" that manages state via external artifacts.

### 2.2 Implicit vs. Explicit Learning
*   **Conflict (v3):** "Active Memory" patterns relied on counters and context accumulation, which leads to "context drift."
*   **Resolution (v4):** Transition to **Explicit Learning**. Improvement occurs through mining successful episodes to train LoRA/QLoRA adapters (Weight Learning), not just prompt engineering.

---

## 3. Maturity Assessment & Porting Targets

### 3.1 High-Maturity Modules (Direct Porting)
These modules are considered "Gold Standard" and should be integrated into v4 with minimal structural changes.

| Component | Source File (Ref) | Maturity | Rationale |
| :--- | :--- | :--- | :--- |
| **Workflow Engine** | `./reference/JARVISv3_ref/backend/ai/workflows/engine.py` | High | Implements FSM/DAG logic, streaming, and checkpoints. |
| **Hardware Service** | `./reference/JARVISv3_ref/backend/core/hardware.py` | High | Advanced NPU/GPU detection and resource pressure handling. |
| **Observability** | `./reference/JARVISv3_ref/backend/core/observability.py` | High | Prometheus metrics, structured logging, and node-level tracing. |
| **Testing Harness** | `./reference/JARVISv3_ref/scripts/validate_backend.py` | High | Comprehensive regression suite runner with XML reporting. |
| **Budget Service** | `./reference/JARVISv2_ref/backend/app/services/budget_service.py` | High | Granular per-category cost tracking and limit enforcement. |

### 3.2 Refactoring Targets (Foundation for v4)
These modules require refactoring to align with the ECF architecture.

*   **Privacy Engine:**
    *   *Strategy:* Combine **v2's Encryption Engine** (AES-GCM/PBKDF2 from `./reference/JARVISv2_ref/backend/app/services/privacy_service.py`) with **v3's Compliance Layer** (Audit logs, GDPR/CCPA retention policies from `./reference/JARVISv3_ref/backend/core/privacy.py`).
    *   *Path:* `v4/backend/core/privacy.py`
*   **Unified Search:**
    *   *Strategy:* Convert `./reference/JARVISv2_ref/backend/app/services/unified_search_service.py` from a global service into a specialized **Executor Tool** for the Agent layer.
*   **Frontend UI:**
    *   *Strategy:* Adopt the `./reference/JARVISv3_ref/frontend/` **React/Tauri stack**. The UI must be refactored to visualize the artifact-driven state (e.g., rendering the `plan.yaml` DAG and `working/` state files).

---

## 4. Infrastructure & Configuration Strategy

### 4.1 Deployment (The v3 Model)
JARVISv4 will adopt the `./reference/JARVISv3_ref/` **Docker architecture** for its superior development and production workflows.
*   **Services:** Backend (API), Redis (Cache), Frontend (Vite/Tauri), and Nginx (Proxy).
*   **Validation Service:** Retain the v3 pattern of a dedicated `validate` service in `./reference/JARVISv3_ref/docker-compose.dev.yml` to run integration tests on startup.

### 4.2 Configuration (The v2 Safety Model)
To prevent accidental production misconfiguration, JARVISv4 will adopt the `./reference/JARVISv2_ref/` **environment strategy**.
*   **Dual Templates:** Maintain `./reference/JARVISv2_ref/.env.example` (Production secure defaults) and `./reference/JARVISv2_ref/.env.dev.example` (Development relaxed settings).
*   **Granularity:** Port the specific flags from v2 for encryption-at-rest, redaction aggressiveness, and budget enforcement levels.

---

## 5. Porting Roadmap

### Phase 1: Foundation
1.  Initialize v4 repository with the `./reference/JARVISv3_ref/` directory structure.
2.  Port `./reference/JARVISv3_ref/scripts/validate_backend.py` and the `./reference/JARVISv3_ref/tests/` structure.
3.  Implement `hardware.py` (based on `./reference/JARVISv3_ref/backend/core/hardware.py`) and `observability.py` (based on `./reference/JARVISv3_ref/backend/core/observability.py`).
4.  Configure Docker and `.env` templates using the Hybrid Model.

### Phase 2: Cognitive Spine
1.  Port and adapt the `WorkflowEngine` (Controller) from `./reference/JARVISv3_ref/`.
2.  Integrate the Budget and Privacy core services from `./reference/JARVISv2_ref/` and `./reference/JARVISv3_ref/`.
3.  Establish the `WorkingStateManager` to manage YAML artifacts on disk.

### Phase 3: Agent & Tool Layer
1.  Convert `./reference/JARVISv2_ref/` Search/LLM providers into v4 Executor Tools.
2.  Port `./reference/JARVISv3_ref/` UI and adapt for ECF visualization.
