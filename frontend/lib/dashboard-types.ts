export type RuntimeStatus =
  | "INITIALIZING"
  | "LIVE"
  | "DEGRADED"
  | "BACKFILLING"
  | "STALE"
  | "ERROR";

export type ServiceStatus = "OK" | "DEGRADED" | "ERROR";
export type BackfillStatus = "PENDING" | "RUNNING" | "SUCCEEDED" | "FAILED";
export type EventSeverity = "INFO" | "WARNING" | "ERROR";
export type CandleSource = "websocket" | "rest_backfill";

export type SymbolStatus = {
  symbol: "BTCUSDT" | "ETHUSDT";
  interval: "1m";
  status: RuntimeStatus;
  last_event_at: string | null;
  last_candle_open_time: string | null;
  freshness_seconds: number | null;
  lag_seconds: number | null;
  latest_price: string | null;
  connection_state: "CONNECTED" | "RECONNECTING" | "DISCONNECTED";
};

export type HealthCheck = {
  name: "API" | "DB";
  status: ServiceStatus;
  detail: string;
};

export type DashboardSummary = {
  system_status: RuntimeStatus;
  symbols: SymbolStatus[];
  total_missing_candle_count: number;
  active_gap_count: number;
  recent_backfill_job_count: number;
  recent_event_count: number;
  environment: string;
  last_updated_at: string;
  health_checks: HealthCheck[];
};

export type Gap = {
  symbol: SymbolStatus["symbol"];
  interval: "1m";
  start_time: string;
  end_time: string;
  missing_candle_count: number;
};

export type BackfillJob = {
  id: number;
  job_type: "initial" | "restart_recovery";
  symbol: SymbolStatus["symbol"];
  interval: "1m";
  status: BackfillStatus;
  range_start: string;
  range_end: string;
  requested_candle_count: number;
  inserted_candle_count: number;
  updated_candle_count: number;
  attempt_count: number;
  started_at: string | null;
  finished_at: string | null;
};

export type CandlePoint = {
  symbol: SymbolStatus["symbol"];
  interval: "1m";
  open_time: string;
  close_price: string;
  source: CandleSource;
};

export type ApplicationEvent = {
  id: number;
  event_time: string;
  severity: EventSeverity;
  event_type: string;
  symbol: SymbolStatus["symbol"] | null;
  interval: "1m" | null;
  message: string;
};

export type SourceMix = {
  source: CandleSource;
  count: number;
};

export type StreamConnectionStatus =
  | "CONNECTING"
  | "LIVE"
  | "RECONNECTING"
  | "DISCONNECTED"
  | "ERROR";

export type DashboardData = {
  summary: DashboardSummary;
  gaps: Gap[];
  backfill_jobs: BackfillJob[];
  candles: CandlePoint[];
  events: ApplicationEvent[];
  source_mix: SourceMix[];
};

export type DashboardFixture = DashboardData;

export type DashboardStreamPayload = {
  event_type: "dashboard_snapshot";
  emitted_at: string;
  system_health: RuntimeStatus;
  symbols: Array<Omit<SymbolStatus, "connection_state">>;
  active_gap_count: number;
  latest_backfill_status: BackfillStatus | null;
};

export type DashboardHeartbeatPayload = {
  event_type: "heartbeat";
  emitted_at: string;
};
