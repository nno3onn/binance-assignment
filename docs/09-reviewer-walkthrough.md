# 09. Reviewer Walkthrough

## Current Implementation Stage
Backend dashboard APIs, SSE, frontend realtime dashboard wiring, smoke verification, and recovery drill automation are implemented through T18.

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

## 5-Minute Recovery Demo
`make recovery-drill` expects backend, frontend, and DB services to already be running with recent BTCUSDT/ETHUSDT candles. It requires DB access through either host `psql` plus `DATABASE_URL`, or Docker Compose access to the `postgres` service.

Run:

```sh
DRILL_SYMBOL=BTCUSDT \
DRILL_GAP_SECONDS=70 \
DRILL_RECOVERY_TRIGGER_URL=http://localhost:8000/<test-only-recovery-trigger> \
make recovery-drill
```

If no HTTP recovery trigger exists, use `DRILL_RECOVERY_COMMAND` to invoke the project-specific recovery command. The drill intentionally fails rather than reporting success when no recovery trigger is configured.

Expected output:
- `[PASS]` backend, frontend, SSE, and DB readiness
- `[PASS]` gap injection and dashboard gap detection
- `[PASS]` restart recovery job recorded and completed
- `[PASS]` missing candle count returns to 0
- `[PASS]` symbol status returns to LIVE
- `[PASS]` duplicate candle count remains 0

## Expected Operational Proof
- Empty DB triggers initial backfill.
- Collector downtime creates a visible gap.
- Restart triggers gap detection and REST recovery.
- Symbol state returns from BACKFILLING to LIVE.
- Missing candle count is 0.
- Duplicate count by unique key is 0.

## Update Rule
Keep this walkthrough aligned with actual commands and screenshots or outputs once implementation exists.
