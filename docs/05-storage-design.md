# 05. Storage Design

## Core Tables
- `candles`: `symbol`, `interval`, `open_time`, OHLCV fields, `close_time`, `source`, timestamps.
- `symbol_runtime_status`: symbol health, last event time, lag, status, error summary.
- `backfill_jobs`: job type, symbol, interval, range, status, counts, error summary.
- `runtime_events`: operational event history.

## Idempotency
`candles` must enforce a unique key on:

```text
symbol + interval + open_time
```

Repeated WebSocket or REST writes must upsert instead of duplicating rows.

## Update Rule
Schema changes must update migrations, repositories, tests, and docs.

## Open Decisions
- Exact numeric precision for OHLCV fields.
- Event retention window.
- Whether to store raw Binance payloads.
