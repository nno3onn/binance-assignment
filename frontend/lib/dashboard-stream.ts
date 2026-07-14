import type {
  DashboardHeartbeatPayload,
  DashboardStreamPayload,
  StreamConnectionStatus
} from "./dashboard-types";

type EventSourceLike = {
  onopen: ((event: Event) => void) | null;
  onerror: ((event: Event) => void) | null;
  addEventListener: (
    type: string,
    listener: (event: Event | MessageEvent<string>) => void
  ) => void;
  close: () => void;
};

type EventSourceFactory = new (url: string) => EventSourceLike;

export type DashboardStreamHandlers = {
  onConnectionChange: (status: StreamConnectionStatus) => void;
  onSnapshot: (payload: DashboardStreamPayload) => void;
  onHeartbeat: (payload: DashboardHeartbeatPayload) => void;
  onStreamError: (message: string) => void;
};

export function connectDashboardStream({
  url,
  eventSourceFactory,
  handlers
}: {
  url: string;
  eventSourceFactory?: EventSourceFactory;
  handlers: DashboardStreamHandlers;
}): { close: () => void } {
  const Source = eventSourceFactory ?? EventSource;
  const source = new Source(url);
  handlers.onConnectionChange("CONNECTING");

  source.onopen = () => {
    handlers.onConnectionChange("LIVE");
  };
  source.onerror = () => {
    handlers.onConnectionChange("RECONNECTING");
    handlers.onStreamError(
      "SSE 연결이 끊겼습니다. 브라우저가 재연결을 시도하고 있습니다."
    );
  };

  source.addEventListener("error", (event) => {
    if (!hasStringData(event)) {
      return;
    }
    const payload = parseJson(event.data);
    handlers.onStreamError(
      isRecord(payload) && typeof payload.message === "string"
        ? payload.message
        : "SSE 오류 이벤트를 수신했습니다."
    );
    handlers.onConnectionChange("ERROR");
  });

  source.addEventListener("dashboard_snapshot", (event) => {
    if (!hasStringData(event)) {
      handlers.onStreamError("잘못된 대시보드 스냅샷을 무시했습니다.");
      return;
    }
    const payload = parseJson(event.data);
    if (isDashboardSnapshot(payload)) {
      handlers.onSnapshot(payload);
      handlers.onConnectionChange("LIVE");
      return;
    }
    handlers.onStreamError("잘못된 대시보드 스냅샷을 무시했습니다.");
  });

  source.addEventListener("heartbeat", (event) => {
    if (!hasStringData(event)) {
      handlers.onStreamError("잘못된 하트비트를 무시했습니다.");
      return;
    }
    const payload = parseJson(event.data);
    if (isHeartbeat(payload)) {
      handlers.onHeartbeat(payload);
      return;
    }
    handlers.onStreamError("잘못된 하트비트를 무시했습니다.");
  });

  return {
    close: () => {
      source.close();
      handlers.onConnectionChange("DISCONNECTED");
    }
  };
}

function parseJson(value: string): unknown {
  try {
    return JSON.parse(value);
  } catch {
    return null;
  }
}

function isDashboardSnapshot(value: unknown): value is DashboardStreamPayload {
  if (!isRecord(value)) {
    return false;
  }
  return (
    value.event_type === "dashboard_snapshot" &&
    typeof value.emitted_at === "string" &&
    typeof value.system_health === "string" &&
    Array.isArray(value.symbols) &&
    typeof value.active_gap_count === "number"
  );
}

function isHeartbeat(value: unknown): value is DashboardHeartbeatPayload {
  if (!isRecord(value)) {
    return false;
  }
  return (
    value.event_type === "heartbeat" && typeof value.emitted_at === "string"
  );
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function hasStringData(
  event: Event | MessageEvent<string>
): event is MessageEvent<string> {
  return "data" in event && typeof event.data === "string";
}
