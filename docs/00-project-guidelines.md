# 00. Project Guidelines

## Fixed Principles
- Optimize for operational reliability over feature volume.
- Keep every Task small, reviewable, and testable.
- Prefer explicit recovery behavior over implicit best effort.
- Treat docs, code, tests, and `TASKS.md` as one contract.
- Use UTC internally.
- Never hardcode secrets.
- Manage backend Python dependencies with uv.
- Use Python 3.12 for backend execution.

## Scope Control
- Build only for BTCUSDT and ETHUSDT 1m candles unless a Task expands scope.
- The dashboard is an operations console for collection, storage, detection, and recovery.
- Do not add trading, auth, alerts, or multi-exchange features.

## Update Rule
Every implementation change must update affected docs in the same Task.

## Open Decisions
- Exact backend test database strategy.
- Whether smoke uses curl only or a browser tool.
- Exact local port conflict policy.
