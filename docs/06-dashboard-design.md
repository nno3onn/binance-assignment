# 06. Dashboard Design

## Core Statement
“이 화면은 코인 가격을 조회하는 화면이 아니라, Binance market data pipeline이 정상적으로 수집, 저장, 탐지, 복구되고 있는지 확인하는 운영 콘솔이다.”

## Required Widgets

| Widget | Purpose | Source | Display | Realtime |
|---|---|---|---|---|
| System Health Summary | Show overall pipeline state | health/status API | Cards | Yes |
| Symbol Pipeline Status | Separate BTCUSDT and ETHUSDT health | runtime status | Table | Yes |
| Data Freshness | Show lag from latest event/candle | candles/status | Cards/Chart | Yes |
| WebSocket Connection State | Show disconnects and reconnects | events/status | Timeline | Yes |
| Gap Detector | Show missing ranges and counts | gap API | Table | Yes |
| Backfill Job Timeline | Prove initial and recovery backfills | backfill jobs | Timeline | Yes |
| Backfill Progress | Show active repair state | backfill jobs | Progress | Yes |
| Ingestion Rate | Detect stalled persistence | candle counts | Chart | Yes |
| REST vs WebSocket Source Mix | Show data lineage | candles.source | Stacked chart | Periodic |
| Duplicate / Upsert Count | Show idempotent behavior | repository metrics | Cards | Yes |
| Latest Market Snapshot | Confirm collected data is market data | candles | Compact cards | Yes |
| Recent Event Log | Explain operational changes | runtime events | Table/Timeline | Yes |
| API / DB Health | Separate service failure from data failure | health checks | Cards | Yes |
| Runbook Panel | Show response guidance per state | docs/status map | Panel | No |

## Update Rule
Dashboard widgets must match API contracts and tests.

## T15 Layout Decision
- Primary row: system health, symbol health, and API/DB health.
- Secondary row: data freshness and source mix.
- Operational tables: symbol pipeline, gap detector, backfill timeline, and event log.
- Market chart is intentionally secondary and fixture-based until API/SSE wiring.
- Health colors use text badges with labels, not color-only status.

## T16 Realtime Decision
- REST provides initial dashboard hydration and supporting candles, gaps, jobs, and events.
- SSE provides realtime `dashboard_snapshot`, `heartbeat`, and `error` updates.
- Browser default EventSource reconnect is used; the UI shows CONNECTING, LIVE, RECONNECTING, DISCONNECTED, or ERROR.
- Last good data remains visible during stream errors or reconnects.

## Open Decisions
- Live chart time windows after API integration.
