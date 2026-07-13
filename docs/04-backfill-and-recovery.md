# 04. Backfill and Recovery

## Fixed Design
- Initial backfill runs when no candles exist for a symbol.
- Initial backfill fetches the recent `INITIAL_BACKFILL_HOURS` window, defaulting to 24 hours.
- Initial backfill writes candles with `source=rest_backfill` through the repository's idempotent upsert path.
- Restart recovery scans for missing 1m ranges and fills them through REST.
- Backfill jobs are recorded with type, symbol, interval, range, status, counts, and errors.
- Candle writes are idempotent, so repeated backfill is safe.

## Recovery Flow

```mermaid
sequenceDiagram
  participant App
  participant DB
  participant Gap as Gap Detector
  participant REST as Binance REST
  App->>DB: Load latest stored candles
  App->>Gap: Detect missing 1m ranges
  alt Gaps found
    Gap->>DB: Create BACKFILLING job
    Gap->>REST: Fetch missing klines
    REST-->>Gap: Return candles
    Gap->>DB: Upsert candles
    Gap->>DB: Mark job completed
  else No gaps
    App->>DB: Mark symbol LIVE
  end
```

## Drill Contract
`scripts/recovery-drill.sh` must eventually prove gap creation, detection, REST repair, LIVE recovery, zero missing candles, and zero duplicates.

## Update Rule
Any recovery behavior change must update this document and the drill.

## Open Decisions
- Maximum REST page size and pagination strategy.
- How far back restart recovery should scan.
- Retry limit before ERROR state.
