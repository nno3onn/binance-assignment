# Binance Market Data Operations Console

This repository is a hiring-assignment implementation plan and harness for a Binance real-time market data collection system.

Dashboard statement:

> “이 화면은 코인 가격을 조회하는 화면이 아니라, Binance market data pipeline이 정상적으로 수집, 저장, 탐지, 복구되고 있는지 확인하는 운영 콘솔이다.”

## Current Status
Harness only. Application functionality is intentionally not implemented yet.

First incomplete Task: `T02 - Scaffold backend project`.

## Stack
- Backend: FastAPI, PostgreSQL.
- Frontend: Next.js App Router, TypeScript, Tailwind CSS, TanStack Query, Recharts.
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

At the harness stage, most commands are guarded placeholders that explain the Task that will activate them. They must not be treated as application validation until the linked Task is complete.

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
