#!/usr/bin/env bash
set -euo pipefail

echo "Recovery drill interface"
cat <<'PLAN'
TODO T18: implement this scenario:
1. Start services.
2. Confirm normal data collection.
3. Stop collector or simulate collector failure.
4. Create a measurable candle gap.
5. Restart collector.
6. Confirm gap detection.
7. Confirm REST backfill execution.
8. Confirm status moves BACKFILLING -> LIVE.
9. Confirm missing candle count is 0.
10. Confirm no duplicates by unique key.
11. Print result summary.
PLAN
exit 1
