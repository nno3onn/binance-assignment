# 03. Data Collection Design

## Fixed Design
- Symbols: BTCUSDT, ETHUSDT.
- Interval: 1m.
- WebSocket is the live source.
- REST backfill is the repair source.
- Store closed candles with `source=websocket` or `source=rest_backfill`.

## Collection Rules
- Reconnect WebSocket with bounded retry/backoff.
- Record disconnect, reconnect, timeout, and parse failures as events.
- Update symbol freshness from the latest accepted candle/event timestamp.
- Never let one symbol hide another symbol's failure state.

## Update Rule
When collector behavior changes, update tests and dashboard status expectations.

## Open Decisions
- Whether to subscribe with combined streams or separate connections.
- Exact stale threshold.
- Retry backoff constants.
