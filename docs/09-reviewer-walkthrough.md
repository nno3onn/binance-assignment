# 09. Reviewer Walkthrough

This is the shortest path for reviewing the repository after clone.

## 1. Clone And Inspect

```sh
git clone <repository-url>
cd binance-assignment
cp .env.example .env
```

Start with:
- `README.md` for the full submission package
- `PRODUCT.md` for scope
- `docs/02-architecture.md` for system shape
- `docs/04-backfill-and-recovery.md` for recovery behavior
- `docs/06-dashboard-design.md` for dashboard intent

## 2. Run Static Verification

```sh
make bootstrap
make check
```

Expected:
- backend ruff, mypy, pytest pass
- frontend ESLint/Prettier, TypeScript, Vitest, Next build pass

## 3. Start Local Services

```sh
make up
```

Open:
- Dashboard: `http://localhost:3000`
- API docs: `http://localhost:8000/docs`
- Health: `http://localhost:8000/api/health`

Important limitation: the compose stack starts PostgreSQL, FastAPI, and Next.js. It does not yet run a production supervisor that automatically launches initial backfill, WebSocket collection, and recovery worker processes. If no candle data exists, smoke checks that require candles will fail honestly.

## 4. Dashboard Review Points

Confirm the UI is operations-first:
- System Health Summary
- BTCUSDT / ETHUSDT runtime state
- Data Freshness and lag
- Symbol Pipeline Status table
- Gap Detector
- Backfill Job Timeline
- Recent Event Log
- Source Mix
- SSE connection state and last good update

The screen should make pipeline health obvious before market price movement.

## 5. Smoke Test

Run after backend/frontend are reachable and at least one candle exists per symbol:

```sh
make smoke
```

Optional overrides:

```sh
SMOKE_API_BASE_URL=http://localhost:8000 \
SMOKE_FRONTEND_URL=http://localhost:3000 \
make smoke
```

Expected checks:
- `/api/health` returns ok
- dashboard summary JSON is valid
- BTCUSDT and ETHUSDT exist in symbol status
- both symbols have at least one candle
- events endpoint returns valid JSON
- SSE endpoint returns `text/event-stream`
- frontend page contains `Market Data Operations Console`

## 6. Recovery Drill

Run only when the system has recent candles and a recovery trigger is available:

```sh
DATABASE_URL=postgresql://binance:binance@localhost:5432/binance_assignment \
DRILL_SYMBOL=BTCUSDT \
DRILL_GAP_SECONDS=70 \
DRILL_RECOVERY_COMMAND='<project-specific recovery command>' \
make recovery-drill
```

The drill:
1. Checks backend, frontend, SSE, and DB readiness.
2. Records row count, latest candle, and duplicate count.
3. Deletes recent candle rows to create a real gap.
4. Confirms the dashboard gap API detects the missing range.
5. Triggers restart recovery.
6. Waits for recovery job completion.
7. Confirms missing count is 0.
8. Confirms symbol status is LIVE.
9. Confirms recovery event history exists.
10. Confirms duplicate candle keys remain 0.

The drill fails instead of pretending success when DB access, stored candles, or a recovery trigger are missing.

## 7. Code Review Focus

Recommended files:
- `backend/app/repositories/sqlalchemy_market_data.py`
- `backend/app/services/backfill.py`
- `backend/app/services/gaps.py`
- `backend/app/services/recovery.py`
- `backend/app/api/dashboard.py`
- `backend/app/api/stream.py`
- `frontend/components/dashboard/operations-dashboard.tsx`
- `frontend/lib/dashboard-api.ts`
- `frontend/lib/dashboard-stream.ts`
- `frontend/lib/dashboard-realtime.ts`
- `scripts/smoke.sh`
- `scripts/recovery-drill.sh`

## 8. Known Review Caveats

- Live Binance calls are not used in unit tests.
- Docker Compose starts API/frontend/PostgreSQL, but not a full worker supervisor.
- Recovery drill requires an explicit recovery trigger command or URL.
- Smoke and recovery checks intentionally fail when live service/data prerequisites are missing.

## 9. Stop Services

```sh
make down
```
