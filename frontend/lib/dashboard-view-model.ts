import type {
  CandlePoint,
  DashboardFixture,
  RuntimeStatus,
  ServiceStatus,
  SymbolStatus
} from "./dashboard-types";

export type Tone = "neutral" | "success" | "warning" | "danger" | "active";

export const statusTone: Record<RuntimeStatus | ServiceStatus, Tone> = {
  INITIALIZING: "neutral",
  LIVE: "success",
  BACKFILLING: "active",
  DEGRADED: "warning",
  STALE: "warning",
  ERROR: "danger",
  OK: "success"
};

export function formatUtc(value: string | null): string {
  if (value === null) {
    return "No event";
  }
  return value.replace("T", " ").replace("Z", " UTC");
}

export function formatDuration(seconds: number | null): string {
  if (seconds === null) {
    return "unknown";
  }
  if (seconds < 60) {
    return `${seconds}s`;
  }
  const minutes = Math.floor(seconds / 60);
  const remainder = seconds % 60;
  return remainder === 0 ? `${minutes}m` : `${minutes}m ${remainder}s`;
}

export function formatPrice(price: string | null): string {
  if (price === null) {
    return "No candle";
  }
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 2
  }).format(Number(price));
}

export function freshnessLabel(symbol: SymbolStatus): string {
  return `${symbol.status} / lag ${formatDuration(symbol.lag_seconds)}`;
}

export function chartSeries(
  fixture: DashboardFixture,
  symbol: SymbolStatus["symbol"]
): Array<{ time: string; close: number; source: CandlePoint["source"] }> {
  return fixture.candles
    .filter((candle) => candle.symbol === symbol)
    .map((candle) => ({
      time: candle.open_time.slice(11, 16),
      close: Number(candle.close_price),
      source: candle.source
    }));
}

export function sourceMixPercentages(
  fixture: DashboardFixture
): Array<{ source: string; count: number; percentage: number }> {
  const total = fixture.source_mix.reduce((sum, item) => sum + item.count, 0);
  if (total === 0) {
    return [];
  }
  return fixture.source_mix.map((item) => ({
    source: item.source,
    count: item.count,
    percentage: Math.round((item.count / total) * 100)
  }));
}

export function dashboardSectionNames() {
  return [
    "System Health Summary",
    "Data Freshness",
    "Symbol Pipeline Status",
    "Gap Detector",
    "Backfill Job Timeline",
    "Recent Candle Chart",
    "Recent Event Log",
    "Source Mix"
  ] as const;
}
