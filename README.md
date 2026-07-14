# Binance Market Data Operations Console

Binance BTCUSDT/ETHUSDT 1m market-data pipeline assignment focused on operational reliability: collection health, freshness, gap detection, backfill/recovery, and reviewer-verifiable checks.

> This is an operations console, not a trading or price-board app.

## Architecture

```mermaid
flowchart LR
  BWS["Binance WebSocket"] --> COL["Collector"]
  BREST["Binance REST API"] --> BF["Initial Backfill"]
  BREST --> REC["Restart Recovery"]
  COL --> ST["Runtime Status"]
  COL --> DB[("PostgreSQL")]
  BF --> DB
  REC --> DB
  ST --> DB
  DB --> API["FastAPI REST API"]
  API --> SSE["SSE Stream"]
  API --> UI["Next.js Operations Dashboard"]
  SSE --> UI
```

Core identity: candles are idempotent by `(symbol, interval, open_time)`.

## Stack

- Backend: Python 3.12, FastAPI, SQLAlchemy, Alembic, uv
- Data store: PostgreSQL
- Binance integrations: REST klines and WebSocket kline stream clients
- Frontend: Next.js App Router, TypeScript, Tailwind CSS, TanStack Query, Zustand, Recharts
- Realtime dashboard transport: Server-Sent Events
- Verification: pytest, mypy, ruff, Vitest, ESLint, Prettier, shell smoke/recovery scripts

## Directory Structure

```text
backend/
  app/api/              Dashboard REST and SSE endpoints
  app/binance/          Binance REST/WebSocket adapters and DTOs
  app/domain/           Domain enums and input models
  app/repositories/     Idempotent persistence layer
  app/services/         Backfill, recovery, gaps, status, events, dashboard queries
  migrations/           Alembic migrations
  tests/                Backend unit/integration tests
frontend/
  app/                  Next.js App Router entry
  components/           Dashboard and reusable UI components
  lib/                  REST/SSE clients, realtime state, view models
  tests/                Vitest tests
docs/                   Architecture, storage, dashboard, recovery, reviewer docs
scripts/                check, smoke, recovery-drill, reset placeholders
```

## Quick Start

Prerequisites:
- Docker and Docker Compose for containerized run
- Node.js 18+ and npm for local frontend checks
- Python 3.12 and uv for local backend checks
- curl and python3 for smoke tests

```sh
cp .env.example .env
make bootstrap
make check
make up
```

Open:
- Frontend: `http://localhost:3000`
- Backend OpenAPI: `http://localhost:8000/docs`
- Backend health: `http://localhost:8000/api/health`

Stop services:

```sh
make down
```

## Environment Variables

Common values are documented in `.env.example`.

| Variable | Default | Purpose |
|---|---:|---|
| `SYMBOLS` | `BTCUSDT,ETHUSDT` | Monitored symbols |
| `CANDLE_INTERVAL` | `1m` | Candle interval |
| `INITIAL_BACKFILL_HOURS` | `24` | Empty-DB initial lookback |
| `DATABASE_URL` | compose default | Backend database URL |
| `BINANCE_REST_BASE_URL` | `https://api.binance.com` | REST endpoint |
| `BINANCE_WS_BASE_URL` | `wss://stream.binance.com:9443` | WebSocket endpoint |
| `NEXT_PUBLIC_API_BASE_URL` | `http://localhost:8000` | Frontend REST base URL |
| `NEXT_PUBLIC_SSE_URL` | `http://localhost:8000/api/dashboard/stream` | Frontend SSE URL |
| `DASHBOARD_SSE_INTERVAL_SECONDS` | `5` | SSE snapshot interval |
| `DASHBOARD_SSE_HEARTBEAT_SECONDS` | `15` | SSE heartbeat interval |

## Main Features

- Alembic schema for candles, runtime status, backfill jobs, and application events
- Idempotent candle upsert with unique `(symbol, interval, open_time)`
- Binance REST client with DTO mapping, timeout, retry, rate-limit, and invalid-response handling
- Initial backfill for empty symbol data using `INITIAL_BACKFILL_HOURS`
- WebSocket collector with validation, keepalive, reconnect, and graceful shutdown primitives
- Runtime status tracking: `INITIALIZING`, `LIVE`, `DEGRADED`, `BACKFILLING`, `STALE`, `ERROR`
- Independent gap detection and restart recovery service
- Event history for collection, backfill, recovery, and invalid-message events
- Read-only dashboard REST API and SSE stream
- Operations dashboard focused on pipeline health, freshness, gaps, recovery, and event history

## Dashboard

The dashboard prioritizes operational health over price movement:
- System Health Summary
- Data Freshness
- Symbol Pipeline Status
- Gap Detector
- Backfill Job Timeline
- Recent Candle Chart
- Recent Event Log
- Source Mix
- SSE connection state and last good update time

REST performs initial hydration; SSE applies realtime dashboard snapshots and heartbeat/error state.

## Backfill And Recovery

Initial backfill:
- Runs only when a symbol has no stored candles.
- Fetches recent klines through Binance REST.
- Stores rows with `source=rest_backfill` through idempotent repository upsert.

Restart recovery:
- Uses gap detection to identify missing 1m candle ranges.
- Fetches only missing ranges through REST.
- Writes recovered rows through bulk upsert.
- Records recovery events and backfill job history.

## API Endpoints

- `GET /api/health`
- `GET /api/dashboard/summary`
- `GET /api/dashboard/symbols`
- `GET /api/dashboard/candles`
- `GET /api/dashboard/gaps`
- `GET /api/dashboard/backfill-jobs`
- `GET /api/dashboard/events`
- `GET /api/dashboard/stream`

## Verification

Canonical local checks:

```sh
make lint
make typecheck
make test
make build
make check
```

`make check` runs backend lint/typecheck/tests and frontend lint/typecheck/tests/build.

## Smoke Test

`make smoke` checks a running system through HTTP:
- backend health
- dashboard summary
- BTCUSDT and ETHUSDT symbol status
- at least one candle per symbol
- events endpoint
- SSE `text/event-stream`
- frontend page and dashboard title

```sh
make up
make smoke
```

Overrides:

```sh
SMOKE_API_BASE_URL=http://localhost:8000 \
SMOKE_FRONTEND_URL=http://localhost:3000 \
SMOKE_RETRIES=20 \
make smoke
```

## Recovery Drill

`make recovery-drill` is a running-system operational drill. It injects a real DB gap by deleting recent candle rows for `DRILL_SYMBOL`, verifies the gap API detects it, triggers recovery, then checks:
- restart recovery job recorded/completed
- missing candle count returns to 0
- symbol status returns to LIVE
- recovery event exists
- duplicate candle keys remain 0

Required:
- running backend, frontend, and PostgreSQL
- recent candles already present
- DB access through host `psql` + `DATABASE_URL`, or Docker Compose `postgres`
- a recovery trigger via `DRILL_RECOVERY_TRIGGER_URL` or `DRILL_RECOVERY_COMMAND`

Example:

```sh
DATABASE_URL=postgresql://binance:binance@localhost:5432/binance_assignment \
DRILL_SYMBOL=BTCUSDT \
DRILL_GAP_SECONDS=70 \
DRILL_RECOVERY_COMMAND='<project-specific recovery command>' \
make recovery-drill
```

The drill fails with `[FAIL]` if prerequisites or a recovery trigger are missing.

## Design Decisions

- Operations first: dashboard explains collection health, freshness, gaps, recovery, and events.
- Idempotency first: duplicate REST/WebSocket writes must not create duplicate candles.
- Source lineage: each candle records `websocket` or `rest_backfill`.
- Recovery is explicit: missing ranges are detected independently before REST repair.
- SSE simplicity: browser EventSource handles reconnect; the UI preserves last good data.
- Tests avoid live Binance calls; external integrations are mocked at unit level.

## Known Limitations

- The repository has service classes for collection/backfill/recovery, but no full production process supervisor that automatically starts collector, initial backfill, and recovery on container boot.
- `make up` starts the FastAPI API, frontend, and PostgreSQL, but it does not by itself seed candle data.
- Recovery drill requires an explicit recovery trigger command or URL because no public admin recovery endpoint is exposed by default.
- Dockerized frontend bakes `NEXT_PUBLIC_*` values at build time; rebuild after changing those values.
- Smoke/recovery drills require real running services and real stored candle data; they intentionally fail rather than using fixtures.

## Future Improvements

- Add a single backend worker entrypoint for initial backfill, collector, and restart recovery orchestration.
- Add a test-only recovery trigger guarded by an explicit environment variable for deterministic reviewer demos.
- Add richer ingestion-rate metrics and source-mix aggregation API.
- Add CI job that builds Docker images and runs a containerized smoke scenario.
- Add retention and archival policy for candles and application events.

## AI Collaboration

AI was used as an implementation partner under a task harness:
- design and task decomposition before coding
- scoped implementation per task
- repository, migration, service, API, dashboard, smoke, and drill tests
- documentation updates after each task

See `docs/08-ai-collaboration-log.md` for task-by-task details.

## Reviewer Walkthrough

For the 5-10 minute review path, start with `docs/09-reviewer-walkthrough.md`.
