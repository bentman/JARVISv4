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
