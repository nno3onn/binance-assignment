import type { DashboardFixture } from "./dashboard-types";

export const dashboardFixture: DashboardFixture = {
  summary: {
    system_status: "DEGRADED",
    environment: "local-review",
    last_updated_at: "2026-07-14T01:18:30Z",
    total_missing_candle_count: 4,
    active_gap_count: 1,
    recent_backfill_job_count: 3,
    recent_event_count: 5,
    health_checks: [
      { name: "API", status: "OK", detail: "FastAPI read endpoints healthy" },
      { name: "DB", status: "OK", detail: "PostgreSQL session responding" }
    ],
    symbols: [
      {
        symbol: "BTCUSDT",
        interval: "1m",
        status: "LIVE",
        last_event_at: "2026-07-14T01:18:21Z",
        last_candle_open_time: "2026-07-14T01:18:00Z",
        freshness_seconds: 9,
        lag_seconds: 2,
        latest_price: "118420.55",
        connection_state: "CONNECTED"
      },
      {
        symbol: "ETHUSDT",
        interval: "1m",
        status: "DEGRADED",
        last_event_at: "2026-07-14T01:14:03Z",
        last_candle_open_time: "2026-07-14T01:14:00Z",
        freshness_seconds: 267,
        lag_seconds: 244,
        latest_price: "3628.15",
        connection_state: "RECONNECTING"
      }
    ]
  },
  gaps: [
    {
      symbol: "ETHUSDT",
      interval: "1m",
      start_time: "2026-07-14T01:15:00Z",
      end_time: "2026-07-14T01:18:00Z",
      missing_candle_count: 4
    }
  ],
  backfill_jobs: [
    {
      id: 42,
      job_type: "restart_recovery",
      symbol: "ETHUSDT",
      interval: "1m",
      status: "RUNNING",
      range_start: "2026-07-14T01:15:00Z",
      range_end: "2026-07-14T01:18:00Z",
      requested_candle_count: 4,
      inserted_candle_count: 2,
      updated_candle_count: 0,
      attempt_count: 1,
      started_at: "2026-07-14T01:18:12Z",
      finished_at: null
    },
    {
      id: 41,
      job_type: "initial",
      symbol: "BTCUSDT",
      interval: "1m",
      status: "SUCCEEDED",
      range_start: "2026-07-13T01:18:00Z",
      range_end: "2026-07-14T01:18:00Z",
      requested_candle_count: 1440,
      inserted_candle_count: 1440,
      updated_candle_count: 0,
      attempt_count: 1,
      started_at: "2026-07-14T01:00:01Z",
      finished_at: "2026-07-14T01:01:44Z"
    },
    {
      id: 40,
      job_type: "initial",
      symbol: "ETHUSDT",
      interval: "1m",
      status: "SUCCEEDED",
      range_start: "2026-07-13T01:18:00Z",
      range_end: "2026-07-14T01:18:00Z",
      requested_candle_count: 1440,
      inserted_candle_count: 1440,
      updated_candle_count: 0,
      attempt_count: 1,
      started_at: "2026-07-14T01:00:01Z",
      finished_at: "2026-07-14T01:01:51Z"
    }
  ],
  candles: [
    {
      symbol: "BTCUSDT",
      interval: "1m",
      open_time: "2026-07-14T01:13:00Z",
      close_price: "118301.12",
      source: "websocket"
    },
    {
      symbol: "BTCUSDT",
      interval: "1m",
      open_time: "2026-07-14T01:14:00Z",
      close_price: "118338.90",
      source: "websocket"
    },
    {
      symbol: "BTCUSDT",
      interval: "1m",
      open_time: "2026-07-14T01:15:00Z",
      close_price: "118399.40",
      source: "websocket"
    },
    {
      symbol: "BTCUSDT",
      interval: "1m",
      open_time: "2026-07-14T01:16:00Z",
      close_price: "118376.32",
      source: "websocket"
    },
    {
      symbol: "BTCUSDT",
      interval: "1m",
      open_time: "2026-07-14T01:17:00Z",
      close_price: "118455.80",
      source: "websocket"
    },
    {
      symbol: "BTCUSDT",
      interval: "1m",
      open_time: "2026-07-14T01:18:00Z",
      close_price: "118420.55",
      source: "websocket"
    },
    {
      symbol: "ETHUSDT",
      interval: "1m",
      open_time: "2026-07-14T01:09:00Z",
      close_price: "3620.41",
      source: "websocket"
    },
    {
      symbol: "ETHUSDT",
      interval: "1m",
      open_time: "2026-07-14T01:10:00Z",
      close_price: "3624.63",
      source: "websocket"
    },
    {
      symbol: "ETHUSDT",
      interval: "1m",
      open_time: "2026-07-14T01:11:00Z",
      close_price: "3629.82",
      source: "websocket"
    },
    {
      symbol: "ETHUSDT",
      interval: "1m",
      open_time: "2026-07-14T01:12:00Z",
      close_price: "3626.04",
      source: "websocket"
    },
    {
      symbol: "ETHUSDT",
      interval: "1m",
      open_time: "2026-07-14T01:13:00Z",
      close_price: "3631.48",
      source: "websocket"
    },
    {
      symbol: "ETHUSDT",
      interval: "1m",
      open_time: "2026-07-14T01:14:00Z",
      close_price: "3628.15",
      source: "websocket"
    }
  ],
  events: [
    {
      id: 101,
      event_time: "2026-07-14T01:18:12Z",
      severity: "WARNING",
      event_type: "recovery_started",
      symbol: "ETHUSDT",
      interval: "1m",
      message: "Restart recovery started for detected ETHUSDT gap."
    },
    {
      id: 100,
      event_time: "2026-07-14T01:18:04Z",
      severity: "WARNING",
      event_type: "websocket_reconnecting",
      symbol: "ETHUSDT",
      interval: "1m",
      message: "ETHUSDT stream reconnecting after stale heartbeat."
    },
    {
      id: 99,
      event_time: "2026-07-14T01:17:59Z",
      severity: "INFO",
      event_type: "websocket_connected",
      symbol: "BTCUSDT",
      interval: "1m",
      message: "BTCUSDT WebSocket stream is connected."
    },
    {
      id: 98,
      event_time: "2026-07-14T01:01:51Z",
      severity: "INFO",
      event_type: "initial_backfill_completed",
      symbol: "ETHUSDT",
      interval: "1m",
      message: "Initial 24h backfill completed for ETHUSDT."
    },
    {
      id: 97,
      event_time: "2026-07-14T01:01:44Z",
      severity: "INFO",
      event_type: "initial_backfill_completed",
      symbol: "BTCUSDT",
      interval: "1m",
      message: "Initial 24h backfill completed for BTCUSDT."
    }
  ],
  source_mix: [
    { source: "websocket", count: 2864 },
    { source: "rest_backfill", count: 2884 }
  ]
};
