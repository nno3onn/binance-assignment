# TASKS

Each Task should be small enough for one focused Codex turn and one commit. Do not start a Task until its prerequisites are complete.

## Phase 1. Harness and bootstrap

- [x] **T01 - Create project harness**
  - Goal: Add product, agent, task, script, CI, and design-doc harness without application functionality.
  - Scope: Repository control files, placeholder scripts, docs skeleton, backend/frontend rule placeholders.
  - Expected files: `PRODUCT.md`, `AGENTS.md`, `TASKS.md`, `README.md`, `.env.example`, `Makefile`, `.gitignore`, `docker-compose.yml`, `scripts/*`, `.github/workflows/ci.yml`, `docs/*`, `backend/AGENTS.md`, `frontend/AGENTS.md`.
  - Done when: Required harness files exist, command names and Task IDs are consistent, first implementation Task is clear.
  - Verification: `make check`
  - Commit message: `chore: add project harness`
  - Prerequisites: None.

- [x] **T02 - Scaffold backend project**
  - Goal: Create minimal FastAPI package structure and dependency metadata.
  - Scope: Backend app entrypoint, config module, test skeleton, lint/typecheck/test commands.
  - Expected files: `backend/pyproject.toml`, `backend/app/main.py`, `backend/app/config.py`, `backend/tests/*`.
  - Done when: Backend health placeholder runs locally and backend lint/typecheck/test commands are real.
  - Verification: `make lint && make typecheck && make test`
  - Commit message: `chore: scaffold backend application`
  - Prerequisites: T01.

- [x] **T03 - Scaffold frontend project**
  - Goal: Create minimal Next.js App Router project with dashboard shell placeholder.
  - Scope: Frontend package metadata, app shell, lint/typecheck/test/build commands.
  - Expected files: `frontend/package.json`, `frontend/app/*`, `frontend/tests/*`.
  - Done when: Frontend build is real and dashboard placeholder page loads.
  - Verification: `make lint && make typecheck && make test && make build`
  - Commit message: `chore: scaffold frontend application`
  - Prerequisites: T01.

## Phase 2. Database and domain model

- [x] **T04 - Add database migrations**
  - Goal: Define PostgreSQL schema for candles, runtime status, backfill jobs, and event history.
  - Scope: Migration tooling and schema only.
  - Expected files: `backend/migrations/*`, `docs/05-storage-design.md`.
  - Done when: Migrations create unique key on `symbol, interval, open_time`.
  - Verification: `make test`
  - Commit message: `feat: add database schema migrations`
  - Prerequisites: T02.

- [x] **T05 - Add candle domain model and repository**
  - Goal: Implement idempotent candle upsert and source tracking.
  - Scope: Domain types, repository, unit tests.
  - Expected files: `backend/app/domain/*`, `backend/app/repositories/*`, `backend/tests/*`.
  - Done when: Duplicate writes do not create duplicate candles.
  - Verification: `make test`
  - Commit message: `feat: add idempotent candle persistence`
  - Prerequisites: T04.

## Phase 3. Binance REST backfill

- [x] **T06 - Add Binance REST client**
  - Goal: Fetch 1m klines for BTCUSDT and ETHUSDT with timeout and error handling.
  - Scope: REST client and mocked tests.
  - Expected files: `backend/app/binance/rest.py`, `backend/tests/*`.
  - Done when: Client maps Binance klines into domain candles.
  - Verification: `make test`
  - Commit message: `feat: add binance rest client`
  - Prerequisites: T05.

- [x] **T07 - Implement initial backfill**
  - Goal: Backfill configured lookback when no stored candles exist.
  - Scope: Backfill service, job state, tests.
  - Expected files: `backend/app/services/backfill.py`, `backend/tests/*`, `docs/04-backfill-and-recovery.md`.
  - Done when: Empty DB creates backfill jobs and stores candles idempotently.
  - Verification: `make test`
  - Commit message: `feat: add initial historical backfill`
  - Prerequisites: T06.

## Phase 4. Binance WebSocket collection

- [x] **T08 - Add Binance WebSocket collector**
  - Goal: Collect live 1m kline updates for BTCUSDT and ETHUSDT.
  - Scope: WebSocket client, reconnect policy, mocked tests.
  - Expected files: `backend/app/binance/websocket.py`, `backend/app/services/collector.py`, `backend/tests/*`.
  - Done when: Closed 1m candles are persisted with `source=websocket`.
  - Verification: `make test`
  - Commit message: `feat: add binance websocket collector`
  - Prerequisites: T05.

## Phase 5. Runtime status, gap detection, and recovery

- [x] **T09 - Implement runtime status tracking**
  - Goal: Track collector runtime state, symbol freshness, last event timestamps, and connection state.
  - Scope: Runtime status service, collector runtime hooks, repository integration, unit tests.
  - Expected files: `backend/app/services/status.py`, `backend/tests/*`, `backend/app/binance/websocket.py`.
  - Done when: Collector can update runtime state through the service without calling repositories directly.
  - Verification: `make test`
  - Commit message: `feat: track collector runtime status`
  - Prerequisites: T05.

- [x] **T10 - Implement restart recovery backfill**
  - Goal: Recover gaps after downtime through REST backfill.
  - Scope: Recovery service, backfill job linkage, tests.
  - Expected files: `backend/app/services/recovery.py`, `backend/tests/*`, `docs/04-backfill-and-recovery.md`.
  - Done when: Gap state moves BACKFILLING to LIVE and missing count becomes 0.
  - Verification: `make test`
  - Commit message: `feat: add restart gap recovery`
  - Prerequisites: T06, T11.

## Phase 6. Runtime status and event history

- [x] **T11 - Implement gap detection**
  - Goal: Detect missing 1m candle ranges per symbol.
  - Scope: Gap scanner and tests.
  - Expected files: `backend/app/services/gaps.py`, `backend/tests/*`.
  - Done when: Intentional missing ranges are reported accurately.
  - Verification: `make test`
  - Commit message: `feat: add candle gap detection`
  - Prerequisites: T05, T09.

- [x] **T12 - Add event history**
  - Goal: Record operational events for disconnects, retries, backfills, gaps, and errors.
  - Scope: Event service and tests.
  - Expected files: `backend/app/services/events.py`, `backend/tests/*`.
  - Done when: Events are queryable in chronological order.
  - Verification: `make test`
  - Commit message: `feat: record runtime event history`
  - Prerequisites: T11.

## Phase 7. Dashboard API and SSE

- [x] **T13 - Add dashboard REST API**
  - Goal: Expose status, gaps, backfill jobs, market snapshot, and events.
  - Scope: FastAPI routers and contract tests.
  - Expected files: `backend/app/api/*`, `backend/tests/*`.
  - Done when: API returns BTCUSDT and ETHUSDT operational state.
  - Verification: `make test`
  - Commit message: `feat: add dashboard api endpoints`
  - Prerequisites: T10, T12.

- [x] **T14 - Add SSE stream**
  - Goal: Stream status/event updates to the dashboard.
  - Scope: SSE endpoint and tests.
  - Expected files: `backend/app/api/stream.py`, `backend/tests/*`.
  - Done when: Clients receive current operational updates without polling.
  - Verification: `make test`
  - Commit message: `feat: add dashboard sse stream`
  - Prerequisites: T13.

## Phase 8. Frontend operations console

- [x] **T15 - Build operations dashboard layout**
  - Goal: Implement dashboard shell focused on pipeline health.
  - Scope: Cards, tables, timelines, charts using API fixtures or typed clients.
  - Expected files: `frontend/app/*`, `frontend/components/*`, `docs/06-dashboard-design.md`.
  - Done when: Dashboard presents health, freshness, gaps, backfill, ingestion, and event widgets.
  - Verification: `make build`
  - Commit message: `feat: build operations dashboard layout`
  - Prerequisites: T03, T13.

- [x] **T16 - Connect dashboard realtime updates**
  - Goal: Wire TanStack Query and SSE to live backend state.
  - Scope: Frontend data hooks and UI states.
  - Expected files: `frontend/lib/*`, `frontend/components/*`, `frontend/tests/*`.
  - Done when: UI updates when symbol status or events change.
  - Verification: `make test && make build`
  - Commit message: `feat: connect dashboard realtime updates`
  - Prerequisites: T14, T15.

## Phase 9. Recovery drill and tests

- [x] **T17 - Implement smoke test**
  - Goal: Verify service health, API, symbol status, stored data, and dashboard access.
  - Scope: `scripts/smoke.sh` real checks.
  - Expected files: `scripts/smoke.sh`, `docs/09-reviewer-walkthrough.md`.
  - Done when: `make smoke` fails on missing health/data/dashboard and passes on a running system.
  - Verification: `make smoke`
  - Commit message: `test: add smoke verification script`
  - Prerequisites: T13, T16.

- [ ] **T18 - Implement recovery drill**
  - Goal: Reproduce collector downtime, gap detection, REST recovery, and duplicate checks.
  - Scope: `scripts/recovery-drill.sh` real scenario.
  - Expected files: `scripts/recovery-drill.sh`, `docs/04-backfill-and-recovery.md`, `docs/09-reviewer-walkthrough.md`.
  - Done when: Drill summarizes gap created, gap recovered, missing count 0, duplicate count 0.
  - Verification: `make recovery-drill`
  - Commit message: `test: add recovery drill automation`
  - Prerequisites: T10, T17.

## Phase 10. Documentation and submission validation

- [ ] **T19 - Finalize README and reviewer docs**
  - Goal: Make setup, run, verification, architecture, and limitations reviewer-friendly.
  - Scope: README and docs updates only.
  - Expected files: `README.md`, `docs/09-reviewer-walkthrough.md`, `docs/*`.
  - Done when: Fresh clone instructions are complete and docs match implementation.
  - Verification: `make check`
  - Commit message: `docs: finalize reviewer documentation`
  - Prerequisites: T18.

- [ ] **T20 - Submission validation pass**
  - Goal: Confirm public repository readiness and final verification.
  - Scope: CI, README, docs, scripts, final smoke/recovery output notes.
  - Expected files: `README.md`, `TASKS.md`, `docs/08-ai-collaboration-log.md`.
  - Done when: `make check`, `make smoke`, and `make recovery-drill` are documented with results.
  - Verification: `make check && make smoke && make recovery-drill`
  - Commit message: `chore: validate submission readiness`
  - Prerequisites: T19.
