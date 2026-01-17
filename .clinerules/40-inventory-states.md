# 40-inventory-states.md

Inventory discipline:
- `SYSTEM_INVENTORY.md` is a status snapshot, not a promise.
- Additive updates only. Do not rewrite history. If a prior entry is wrong, append a correction with date + evidence pointer.
- Promote a capability only when supported by validation evidence (tests, harness runs, or reproducible runtime checks).
- Skips/warnings do not count as validation unless they are explicitly the intended outcome.
- Keep entries terse and concrete:
  - Capability name
  - Current state (pick one and use consistently)
  - Location (path(s))
  - Validation (exact command + minimal excerpt pointer)
  - Notes (optional, 1–2 lines)

States:
- Planned: intent only, not implemented
- Implemented: code exists, not yet validated end-to-end
- Verified: validated with evidence (command + excerpt)
- Deferred: intentionally postponed (reason noted)

Update rules:
- Add new entries; don’t rewrite history.
- If a prior entry is wrong, append a correction with the date and the evidence pointer.
- Keep inventory entries terse: what exists, how it was validated, where it lives.
