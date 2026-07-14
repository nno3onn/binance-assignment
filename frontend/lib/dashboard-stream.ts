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
    handlers.onStreamError("SSE connection lost; browser reconnect is active.");
  };

  source.addEventListener("error", (event) => {
    if (!hasStringData(event)) {
      return;
    }
    const payload = parseJson(event.data);
    handlers.onStreamError(
      isRecord(payload) && typeof payload.message === "string"
        ? payload.message
        : "SSE error event received"
    );
    handlers.onConnectionChange("ERROR");
  });

  source.addEventListener("dashboard_snapshot", (event) => {
    if (!hasStringData(event)) {
      handlers.onStreamError("Invalid dashboard snapshot ignored.");
      return;
    }
    const payload = parseJson(event.data);
    if (isDashboardSnapshot(payload)) {
      handlers.onSnapshot(payload);
      handlers.onConnectionChange("LIVE");
      return;
    }
    handlers.onStreamError("Invalid dashboard snapshot ignored.");
  });

  source.addEventListener("heartbeat", (event) => {
    if (!hasStringData(event)) {
      handlers.onStreamError("Invalid heartbeat ignored.");
      return;
    }
    const payload = parseJson(event.data);
    if (isHeartbeat(payload)) {
      handlers.onHeartbeat(payload);
      return;
    }
    handlers.onStreamError("Invalid heartbeat ignored.");
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
