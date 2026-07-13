# 01. Requirements and Scope

## Functional Requirements
- Collect BTCUSDT and ETHUSDT 1m Binance market data in real time.
- Backfill when the database is empty.
- Recover missing ranges after downtime.
- Store candles idempotently in PostgreSQL.
- Show operational status in a realtime dashboard.
- Default initial backfill lookback is the recent 24 hours and is configurable with `INITIAL_BACKFILL_HOURS`.

## Nonfunctional Requirements
- Repeatable local execution through Docker Compose.
- Canonical validation through `make check`, `make smoke`, and `make recovery-drill`.
- Observable failure states for stale data, gaps, backfill, and service errors.

## Excluded
- Trading decisions, order execution, user accounts, cloud deployment, and alert delivery.

## Update Rule
If implementation changes requirement interpretation, update this document and `TASKS.md`.

## Open Decisions
- Whether to persist partial in-progress candles or only closed 1m candles.
- Final local port conflict policy.
- Exact retention policy for runtime events.
