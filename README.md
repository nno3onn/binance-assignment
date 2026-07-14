# Binance Market Data Operations Console

This repository is a hiring-assignment implementation plan and harness for a Binance real-time market data collection system.

Dashboard statement:

> “이 화면은 코인 가격을 조회하는 화면이 아니라, Binance market data pipeline이 정상적으로 수집, 저장, 탐지, 복구되고 있는지 확인하는 운영 콘솔이다.”

## Current Status
Backend data, dashboard API, SSE stream, and frontend operations console are implemented through T16.

First incomplete Task: `T17 - Implement smoke test`.

## Stack
- Backend: FastAPI, PostgreSQL.
- Python: 3.12 managed by uv.
- Frontend: Next.js App Router, TypeScript, Tailwind CSS, TanStack Query, Zustand, Recharts.
- Frontend tests: Vitest.
- Realtime: Binance WebSocket, dashboard SSE.
- Backfill: Binance REST API.
- Runtime: Docker Compose.

## Commands

```sh
make bootstrap
make up
make down
make logs
make lint
make typecheck
make test
make build
make check
make smoke
make reset-db
make recovery-drill
```

At the current stage, backend and frontend lint, typecheck, tests, and frontend build are active. Smoke, database reset, and recovery drill commands remain guarded placeholders until their linked Tasks are complete.

## Database Migrations

Backend migrations use Alembic and target PostgreSQL. During local unit tests they are also exercised against temporary SQLite databases so migration up, down, and re-run behavior can be verified without Docker.

From `backend/`:

```sh
uv run alembic upgrade head
uv run alembic downgrade base
```

## Persistence Layer

The backend repository layer uses SQLAlchemy ORM models and keeps candle writes idempotent with the `symbol + interval + open_time` identity. Repository unit tests run against SQLite and avoid PostgreSQL-only SQL in the public repository API.

## Binance REST Client

The Binance REST client is an adapter only. It does not call repositories or services. It provides `ping`, `get_server_time`, and `get_klines`, maps kline arrays into internal DTOs, and handles timeout, network, 4xx, 5xx, 429, invalid response, and bounded exponential-backoff retry behavior.

## Initial Backfill

Initial backfill runs only when a symbol has no stored candles. It fetches the recent `INITIAL_BACKFILL_HOURS` window through the Binance REST client, maps DTOs into candle domain inputs, and persists them through the idempotent repository path with `source=rest_backfill`.

## Binance WebSocket Collector

The WebSocket collector subscribes to combined Binance kline streams for configured symbols and emits validated internal DTOs. It handles keepalive ping/pong, graceful shutdown, invalid message filtering, and bounded exponential reconnects. It does not persist data or update runtime status in T08.

## Event History

The event history layer records operational events such as WebSocket connect/disconnect/reconnect, invalid messages, initial backfill completion, and restart recovery completion/failure. Event recording is best-effort so a temporary event-store failure does not stop collection or recovery.

## Dashboard REST API

Read-only dashboard endpoints:

- `GET /api/health`
- `GET /api/dashboard/summary`
- `GET /api/dashboard/symbols`
- `GET /api/dashboard/candles`
- `GET /api/dashboard/gaps`
- `GET /api/dashboard/backfill-jobs`
- `GET /api/dashboard/events`
- `GET /api/dashboard/stream` for SSE dashboard snapshots and heartbeat events

## Frontend Realtime Dashboard

The frontend uses `NEXT_PUBLIC_API_BASE_URL` for initial REST hydration and `NEXT_PUBLIC_SSE_URL` for realtime dashboard snapshots. REST loads the initial dashboard state, recent candles, gaps, backfill jobs, and events. SSE then updates the dashboard summary and symbol statuses through `dashboard_snapshot`, `heartbeat`, and `error` events without REST polling.

Required frontend environment variables:

```sh
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
NEXT_PUBLIC_SSE_URL=http://localhost:8000/api/dashboard/stream
```

## Required Reading Before Work
1. `PRODUCT.md`
2. `AGENTS.md`
3. `TASKS.md`
4. Relevant `docs/*`

## Design Docs
- `docs/00-project-guidelines.md`
- `docs/01-requirements-and-scope.md`
- `docs/02-architecture.md`
- `docs/03-data-collection-design.md`
- `docs/04-backfill-and-recovery.md`
- `docs/05-storage-design.md`
- `docs/06-dashboard-design.md`
- `docs/07-testing-strategy.md`
- `docs/08-ai-collaboration-log.md`
- `docs/09-reviewer-walkthrough.md`

## Submission Criteria
- Public GitHub repository is accessible.
- README, docs, code, tests, and `TASKS.md` are consistent.
- `make check`, `make smoke`, and `make recovery-drill` pass after implementation Tasks are complete.
