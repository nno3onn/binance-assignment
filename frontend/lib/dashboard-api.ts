import type {
  ApplicationEvent,
  BackfillJob,
  CandlePoint,
  CandleSource,
  DashboardData,
  DashboardSummary,
  Gap,
  HealthCheck,
  RuntimeStatus,
  SymbolStatus
} from "./dashboard-types";

type Env = Record<string, string | undefined>;

type HealthResponse = {
  status: string;
  environment: string;
  symbols: string[];
  interval: string;
  initial_backfill_hours: number;
};

type SymbolStatusResponse = Omit<SymbolStatus, "connection_state">;

type DashboardSummaryResponse = {
  system_status: RuntimeStatus;
  symbols: SymbolStatusResponse[];
  total_missing_candle_count: number;
  active_gap_count: number;
  recent_backfill_job_count: number;
  recent_event_count: number;
};

type CandlesResponse = {
  symbol: SymbolStatus["symbol"];
  interval: "1m";
  candles: Array<{
    symbol: SymbolStatus["symbol"];
    interval: "1m";
    open_time: string;
    close_price: string;
    source: CandleSource;
  }>;
};

type GapsResponse = {
  gaps: Gap[];
  total_missing_candle_count: number;
};

type BackfillJobsResponse = {
  jobs: BackfillJob[];
};

type EventsResponse = {
  events: Array<
    ApplicationEvent & {
      metadata_json?: Record<string, unknown>;
      created_at?: string;
    }
  >;
};

export function getApiBaseUrl(env: Env = process.env): string {
  return (env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000").replace(
    /\/$/,
    ""
  );
}

export function getSseUrl(env: Env = process.env): string {
  return (
    env.NEXT_PUBLIC_SSE_URL ?? `${getApiBaseUrl(env)}/api/dashboard/stream`
  );
}

export async function fetchDashboardData(
  fetcher: typeof fetch = fetch,
  apiBaseUrl = getApiBaseUrl()
): Promise<DashboardData> {
  const health = await fetchJson<HealthResponse>(
    fetcher,
    `${apiBaseUrl}/api/health`
  );
  const summary = await fetchJson<DashboardSummaryResponse>(
    fetcher,
    `${apiBaseUrl}/api/dashboard/summary`
  );
  const [btcCandles, ethCandles, gaps, backfillJobs, events] =
    await Promise.all([
      fetchJson<CandlesResponse>(
        fetcher,
        `${apiBaseUrl}/api/dashboard/candles?symbol=BTCUSDT&interval=1m&limit=60`
      ),
      fetchJson<CandlesResponse>(
        fetcher,
        `${apiBaseUrl}/api/dashboard/candles?symbol=ETHUSDT&interval=1m&limit=60`
      ),
      fetchJson<GapsResponse>(
        fetcher,
        `${apiBaseUrl}/api/dashboard/gaps?interval=1m`
      ),
      fetchJson<BackfillJobsResponse>(
        fetcher,
        `${apiBaseUrl}/api/dashboard/backfill-jobs?limit=20`
      ),
      fetchJson<EventsResponse>(
        fetcher,
        `${apiBaseUrl}/api/dashboard/events?limit=20`
      )
    ]);

  const candles = [...btcCandles.candles, ...ethCandles.candles];
  return {
    summary: toDashboardSummary(summary, health, true),
    gaps: gaps.gaps,
    backfill_jobs: backfillJobs.jobs,
    candles,
    events: events.events,
    source_mix: toSourceMix(candles)
  };
}

async function fetchJson<T>(fetcher: typeof fetch, url: string): Promise<T> {
  const response = await fetcher(url, {
    headers: { Accept: "application/json" },
    cache: "no-store"
  });
  if (!response.ok) {
    throw new Error(`Dashboard API request failed: ${response.status}`);
  }
  return (await response.json()) as T;
}

function toDashboardSummary(
  summary: DashboardSummaryResponse,
  health: HealthResponse,
  dbHealthy: boolean
): DashboardSummary {
  return {
    ...summary,
    environment: health.environment,
    last_updated_at: new Date().toISOString(),
    health_checks: [
      toHealthCheck("API", health.status === "ok", "FastAPI health endpoint"),
      toHealthCheck("DB", dbHealthy, "Dashboard read endpoints")
    ],
    symbols: summary.symbols.map((symbol) => ({
      ...symbol,
      connection_state: symbol.status === "LIVE" ? "CONNECTED" : "RECONNECTING"
    }))
  };
}

function toHealthCheck(
  name: HealthCheck["name"],
  ok: boolean,
  detail: string
): HealthCheck {
  return {
    name,
    status: ok ? "OK" : "ERROR",
    detail: ok ? `${detail} healthy` : `${detail} unavailable`
  };
}

function toSourceMix(candles: CandlePoint[]) {
  const counts = candles.reduce<Record<CandleSource, number>>(
    (acc, candle) => {
      acc[candle.source] += 1;
      return acc;
    },
    { websocket: 0, rest_backfill: 0 }
  );
  return Object.entries(counts)
    .filter(([, count]) => count > 0)
    .map(([source, count]) => ({
      source: source as CandleSource,
      count
    }));
}
