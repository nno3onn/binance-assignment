# 09. Reviewer Walkthrough

## Current Implementation Stage
Backend dashboard APIs, SSE, frontend realtime dashboard wiring, and smoke verification are implemented through T17.

## What to Review First
1. `PRODUCT.md` for product goal and scope.
2. `TASKS.md` for implementation order.
3. `docs/02-architecture.md` for system structure.
4. `docs/04-backfill-and-recovery.md` for recovery behavior.
5. `docs/06-dashboard-design.md` for operations console design.

## Final Verification Path
After implementation Tasks are complete:

```sh
make bootstrap
make up
make check
make smoke
make recovery-drill
```

## Smoke Verification
`make smoke` expects backend and frontend services to already be running. It checks:
- backend `/api/health`
- dashboard summary, symbols, candles, and events
- BTCUSDT and ETHUSDT presence
- at least one candle per symbol
- SSE `text/event-stream`
- frontend root page and dashboard title

The script uses `curl` and `python3`; `jq` is not required. Override URLs with `SMOKE_API_BASE_URL` and `SMOKE_FRONTEND_URL`.

## Expected Operational Proof
- Empty DB triggers initial backfill.
- Collector downtime creates a visible gap.
- Restart triggers gap detection and REST recovery.
- Symbol state returns from BACKFILLING to LIVE.
- Missing candle count is 0.
- Duplicate count by unique key is 0.

## Update Rule
Keep this walkthrough aligned with actual commands and screenshots or outputs once implementation exists.
