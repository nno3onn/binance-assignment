# 07. Testing Strategy

## Layers
- Unit: domain mapping, gap detection, idempotent upsert decisions.
- Integration: PostgreSQL migrations, repository writes, API contracts.
- Service: REST backfill and WebSocket collector with mocked Binance responses.
- Frontend: dashboard state rendering and realtime update handling.
- Smoke: health, API, symbols, stored data, dashboard access.
- Recovery drill: downtime gap creation and repair.

## Canonical Commands
- `make check`: lint, typecheck, tests, frontend build.
- `make smoke`: running-system verification.
- `make recovery-drill`: operational recovery scenario.

## Tooling
- Backend package manager: uv.
- Backend Python version: 3.12.
- Frontend test runner: Vitest.

## Update Rule
Every new behavior needs a corresponding test or an explicit documented reason.

## Open Decisions
- Exact backend test database strategy.
- Whether smoke uses curl only or a browser tool.
