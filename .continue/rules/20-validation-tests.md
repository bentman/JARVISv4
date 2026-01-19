# 20-validation-tests.md

- Prefer existing harnesses:
  - Primary backend harness: `scripts/validate_backend.py`
  - Tests: `tests/unit/`, `tests/integration/`, `tests/agentic/`
- Don’t invent new scripts or one-off validators unless explicitly requested.
- Warnings are backlog, not blockers, unless they break correctness, CI, or user-visible behavior.
- Host vs Docker separation:
  - Host runs may skip due to missing system deps; note skips briefly.
  - End-to-end voice/container validation belongs in Docker; don’t force host parity.
- When reporting a pass/fail, include the exact command and the minimal excerpt showing the result.
- If validation is slow, run the smallest targeted test first (single test file/case) before broader suites.
