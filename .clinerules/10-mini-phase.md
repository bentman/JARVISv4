# 10-mini-phase.md

Mini-phase format:
- One objective only.
- Discovery first, then proposal (when risk is non-trivial), then implement, then validate, then stop.

Approval gates:
- If touching multiple files, core services, build pipelines, Docker, or test harnesses: proposal-only before edits.
- Proposal must list: exact files to touch + why, minimal validation command(s), expected evidence.

Validation discipline:
- Run the smallest relevant check first; expand only after it passes.
- If attempts repeat without changing the failure mode, stop and propose a different strategy.

Stop/report:
- Stop immediately when the objective is met and validated with evidence.
- Otherwise stop at the next approval gate with a short proposal.
- Evidence excerpts: max 10 lines per item; avoid full logs unless required for failure analysis.
