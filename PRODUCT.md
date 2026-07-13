# PRODUCT

## Problem
Internal crypto data operators need a reliable way to collect Binance market data and understand whether the pipeline is healthy, current, and recoverable after downtime.

## Users
Primary user: internal cryptocurrency data operations team.

## Core Scenarios
- Start the system with an empty database and backfill recent BTCUSDT/ETHUSDT 1m candles.
- Collect live BTCUSDT/ETHUSDT 1m data from Binance WebSocket.
- Restart after downtime and recover missing candle ranges through REST backfill.
- Detect stale symbols, gaps, failed backfills, duplicate writes, and service health issues from one dashboard.
- Run a repeatable recovery drill before submission.

## Minimum Requirements
- Symbols: BTCUSDT, ETHUSDT.
- Interval: 1m.
- Real-time collection via Binance WebSocket.
- Initial and restart recovery backfill via Binance REST API.
- PostgreSQL storage with `symbol + interval + open_time` unique key.
- FastAPI backend, Next.js App Router frontend, TypeScript, Tailwind CSS, TanStack Query, Recharts, SSE, Docker Compose.

## P0 Scope
- Idempotent candle persistence.
- Initial backfill and restart gap recovery.
- Symbol health states: INITIALIZING, LIVE, DEGRADED, BACKFILLING, STALE, ERROR.
- Operations dashboard focused on freshness, gaps, backfill jobs, ingestion, and runtime events.
- One-command local run and verification harness.

## P1 Scope
- Recovery drill automation.
- Source tracking: `websocket` or `rest_backfill`.
- Recent event history and runbook-oriented dashboard states.
- CI for lint, typecheck, test, build, and Docker Compose config validation.

## Out of Scope
- Trading, order placement, alerts, authentication, multi-exchange support, advanced technical indicators, and production cloud deployment.

## Success Criteria
- A reviewer can run the project locally with documented commands.
- The system visibly backfills an empty database.
- The system visibly recovers a gap after collector downtime.
- Dashboard state matches stored data and runtime status.
- `make check` and `make smoke` provide the canonical verification path.

## Submission Done Criteria
- GitHub repository is public and accessible.
- README documents setup, run, architecture, verification, and limitations.
- Docs, code, tests, and TASKS.md are consistent.
- Recovery drill result is reproducible.

## Dashboard Statement
“이 화면은 코인 가격을 조회하는 화면이 아니라, Binance market data pipeline이 정상적으로 수집, 저장, 탐지, 복구되고 있는지 확인하는 운영 콘솔이다.”
