# AGENTS

These rules control all Codex work in this repository.

## Required Workflow
- Before each task, read `PRODUCT.md`, `AGENTS.md`, `TASKS.md`, and the relevant docs.
- Perform exactly one Task at a time.
- Do not add features that are not named in the active Task.
- If a Task is too large, split it in `TASKS.md` before implementation.
- Do not change the existing architecture without updating the relevant docs first.
- Before editing, inspect related files and existing tests.
- After implementation, add or update relevant tests.
- Do not mark a Task complete unless `make check` succeeds.
- Do not delete, skip, or weaken failing tests to pass validation.
- Do not hardcode secrets, API keys, or environment-specific values.
- Do not ignore external API errors, timeout, retry, or rate-limit behavior.
- Database writes must be idempotent.
- Use UTC internally for dates and times.
- After completing a Task, update the checkbox in `TASKS.md` and append to `docs/08-ai-collaboration-log.md`.
- Avoid unrelated large refactors.

## Reporting Format
Final responses after a Task must briefly include:
- Changed files.
- Verification result.
- Remaining risks.
- Next Task.

## Scope Guardrails
- This is an operations-grade Binance market data collection assignment, not a trading app.
- Dashboard work must emphasize pipeline health, freshness, gaps, backfill, and recovery.
- Keep docs short and update them when implementation changes.
