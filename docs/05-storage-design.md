# 05. Storage Design

## Core Tables

### `candles`
- Reason: canonical 1m market data used by backfill, WebSocket collection, gap detection, and dashboard snapshots.
- Primary key: `id`.
- Unique key: `symbol, interval, open_time`.
- Foreign keys: none.
- Indexes: `symbol, interval, open_time`; `symbol, interval, close_time`; `source`.
- Constraints: `source in ('websocket', 'rest_backfill')`.

### `symbol_runtime_status`
- Reason: current per-symbol pipeline state for operations cards and stale/degraded detection.
- Primary key: `id`.
- Unique key: `symbol, interval`.
- Foreign keys: none.
- Indexes: `status`; `symbol, interval`.
- Constraints: `status in ('INITIALIZING', 'LIVE', 'DEGRADED', 'BACKFILLING', 'STALE', 'ERROR')`.

### `backfill_jobs`
- Reason: records initial backfill and restart recovery backfill execution history.
- Primary key: `id`.
- Unique key: none; multiple jobs per symbol/range are allowed for retry history.
- Foreign keys: none.
- Indexes: `symbol, interval, status`; `job_type`; `symbol, interval, range_start, range_end`.
- Constraints: `job_type in ('initial', 'restart_recovery')`; `status in ('PENDING', 'RUNNING', 'SUCCEEDED', 'FAILED')`.

### `application_events`
- Reason: event log source for the operations dashboard timeline.
- Primary key: `id`.
- Unique key: none; event history is append-only.
- Foreign keys: optional `backfill_job_id -> backfill_jobs.id` with `ON DELETE SET NULL`.
- Indexes: `event_time`; `event_type`; `symbol, interval`; `backfill_job_id`.
- Constraints: `severity in ('INFO', 'WARN', 'ERROR')`.

## Idempotency
`candles` must enforce a unique key on:

```text
symbol + interval + open_time
```

Repeated WebSocket or REST writes must upsert instead of duplicating rows.

## Timestamp Rule
All timestamps are stored as timezone-aware UTC timestamps. Application code must provide UTC datetimes when inserting market or runtime data.

## Update Rule
Schema changes must update migrations, repositories, tests, and docs.

## Open Decisions
- Event retention window.
- Whether to store raw Binance payloads.
