# 00-guardrails.md

- Treat `Project.md` as the current repo intent; follow the `Project.md` Section 2 tree for paths.
- Legacy code is read-only: `reference/JARVISv2_ref/`, `reference/JARVISv3_ref/`.
- No guessing. If uncertain, show what was inspected and stop for direction.
- No scope expansion. One objective per mini-phase; adjacent work becomes a new mini-phase.
- Prefer existing patterns in-repo over inventing new ones.
- No web/MCP lookups unless explicitly requested by the User.
- Truth = evidence. Any completion claim must be backed by a command run and a minimal excerpt.
- Keep outputs small: only the lines needed to prove the claim; no large log pastes unless diagnosing failure.
- Avoid terms: skeleton, stub, placeholder, shim. Prefer: baseline, foundation, initial.
- Repo anchors:
  - Backend entrypoint: `backend/main.py`
  - Validation harness: `scripts/validate_backend.py`
  - Tests live under: `tests/`
