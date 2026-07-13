# 08. AI Collaboration Log

Record AI-generated changes and human verification here. Keep entries short.

| Date | Task | AI Contribution | Human/Reviewer Verification | Result |
|---|---|---|---|---|
| 2026-07-14 | T01 | Created harness structure, docs, scripts, and CI placeholders. | Pending user review. | In progress |
| 2026-07-14 | T02 | Scaffolded uv-based FastAPI backend, config, health test, and backend check commands. | `make lint && make typecheck && make test && make check` passed. | Complete |
| 2026-07-14 | T03 | Scaffolded Next.js App Router frontend with TypeScript, Tailwind CSS, TanStack Query, Zustand, ESLint, Prettier, and Vitest. | `make lint && make typecheck && make test && make build && make check` passed. | Complete |
| 2026-07-14 | T04 | Added Alembic migrations for candles, runtime status, backfill jobs, and application events. | Alembic CLI up/down/re-upgrade passed on SQLite; `make check` passed. | Complete |
| 2026-07-14 | T05 | Added SQLAlchemy ORM models, repository interface, idempotent repository implementation, and repository tests. | `make lint && make typecheck && make test && make check` passed. | Complete |
| 2026-07-14 | T06 | Added Binance REST adapter, DTOs, error handling, timeout, and bounded exponential retry tests. | `make lint && make typecheck && make test && make check` passed. | Complete |
| 2026-07-14 | T07 | Added initial backfill service using Binance REST DTOs and repository idempotent upsert. | `make lint && make typecheck && make test && make check` passed. | Complete |
| 2026-07-14 | T08 | Added Binance WebSocket collector, kline DTO parsing, keepalive, reconnect, shutdown, and mocked collector tests. | `make check` passed. | Complete |
| 2026-07-14 | T09 | Added runtime status service, connection state tracking, freshness calculation, and collector runtime hooks. | `make check` passed. | Complete |

## Rule
After each completed Task, append one row describing what AI changed and how it was verified.
