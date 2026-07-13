# Backend AGENTS

- Follow root `AGENTS.md`.
- Backend stack is FastAPI with PostgreSQL.
- Keep collection, backfill, persistence, API, and runtime status responsibilities separated.
- All candle writes must use the `symbol + interval + open_time` idempotency key.
- External Binance clients must handle timeout, retryable errors, rate limits, and structured error reporting.
- Backend tests must cover domain logic before live network behavior.
