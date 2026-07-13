# 09. Reviewer Walkthrough

## Current Harness Stage
Application functionality is intentionally not implemented yet. The repository currently defines the control structure for later implementation.

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

## Expected Operational Proof
- Empty DB triggers initial backfill.
- Collector downtime creates a visible gap.
- Restart triggers gap detection and REST recovery.
- Symbol state returns from BACKFILLING to LIVE.
- Missing candle count is 0.
- Duplicate count by unique key is 0.

## Update Rule
Keep this walkthrough aligned with actual commands and screenshots or outputs once implementation exists.
