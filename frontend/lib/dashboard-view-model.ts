import type {
  BackfillStatus,
  CandlePoint,
  CandleSource,
  DashboardFixture,
  EventSeverity,
  RuntimeStatus,
  ServiceStatus,
  StreamConnectionStatus,
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
    return "이벤트 없음";
  }
  return value.replace("T", " ").replace("Z", " UTC");
}

export function formatDuration(seconds: number | null): string {
  if (seconds === null) {
    return "알 수 없음";
  }
  if (seconds < 60) {
    return `${seconds}초`;
  }
  const minutes = Math.floor(seconds / 60);
  const remainder = seconds % 60;
  return remainder === 0 ? `${minutes}분` : `${minutes}분 ${remainder}초`;
}

export function formatPrice(price: string | null): string {
  if (price === null) {
    return "캔들 없음";
  }
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 2
  }).format(Number(price));
}

export function freshnessLabel(symbol: SymbolStatus): string {
  return `${runtimeStatusLabel(symbol.status)} / 지연 ${formatDuration(
    symbol.lag_seconds
  )}`;
}

export function runtimeStatusLabel(status: RuntimeStatus): string {
  return {
    INITIALIZING: "초기화 중",
    LIVE: "정상",
    BACKFILLING: "백필 진행 중",
    DEGRADED: "성능 저하",
    STALE: "데이터 지연",
    ERROR: "오류"
  }[status];
}

export function serviceStatusLabel(status: ServiceStatus): string {
  return {
    OK: "정상",
    DEGRADED: "성능 저하",
    ERROR: "오류"
  }[status];
}

export function connectionStatusLabel(status: StreamConnectionStatus): string {
  return {
    CONNECTING: "연결 중",
    LIVE: "연결됨",
    RECONNECTING: "재연결 중",
    DISCONNECTED: "연결 끊김",
    ERROR: "오류"
  }[status];
}

export function symbolConnectionStatusLabel(
  status: SymbolStatus["connection_state"]
): string {
  return {
    CONNECTED: "연결됨",
    RECONNECTING: "재연결 중",
    DISCONNECTED: "연결 끊김"
  }[status];
}

export function backfillStatusLabel(status: BackfillStatus): string {
  return {
    PENDING: "대기 중",
    RUNNING: "진행 중",
    SUCCEEDED: "완료",
    FAILED: "실패"
  }[status];
}

export function severityLabel(severity: EventSeverity): string {
  return {
    INFO: "정보",
    WARNING: "주의",
    ERROR: "오류"
  }[severity];
}

export function candleSourceLabel(source: CandleSource): string {
  return {
    websocket: "웹소켓",
    rest_backfill: "REST 백필"
  }[source];
}

export function backfillJobTypeLabel(jobType: string): string {
  return (
    {
      initial: "초기 백필",
      restart_recovery: "재시작 복구"
    }[jobType] ?? jobType
  );
}

export function eventTypeLabel(eventType: string): string {
  return (
    {
      websocket_connected: "웹소켓 연결됨",
      websocket_disconnected: "웹소켓 연결 끊김",
      websocket_reconnecting: "웹소켓 재연결 중",
      initial_backfill_started: "초기 백필 시작",
      initial_backfill_completed: "초기 백필 완료",
      recovery_started: "복구 시작",
      recovery_completed: "복구 완료",
      recovery_failed: "복구 실패",
      invalid_message_received: "잘못된 메시지 수신"
    }[eventType] ?? eventType.replaceAll("_", " ")
  );
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
): Array<{ source: CandleSource; count: number; percentage: number }> {
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
    "시스템 상태 요약",
    "데이터 최신성",
    "심볼별 파이프라인 상태",
    "누락 데이터 현황",
    "백필 작업 이력",
    "최근 캔들 차트",
    "최근 이벤트",
    "데이터 수집 경로"
  ] as const;
}
