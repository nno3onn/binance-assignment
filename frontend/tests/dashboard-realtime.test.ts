import { describe, expect, it, vi } from "vitest";

import {
  fetchDashboardData,
  getApiBaseUrl,
  getSseUrl
} from "@/lib/dashboard-api";
import { mergeSnapshot } from "@/lib/dashboard-realtime";
import { connectDashboardStream } from "@/lib/dashboard-stream";
import { dashboardFixture } from "@/lib/dashboard-fixture";
import type {
  DashboardHeartbeatPayload,
  DashboardStreamPayload,
  StreamConnectionStatus
} from "@/lib/dashboard-types";

class FakeEventSource {
  static instances: FakeEventSource[] = [];

  onopen: ((event: Event) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;
  readonly listeners = new Map<
    string,
    Array<(event: MessageEvent<string>) => void>
  >();
  closed = false;

  constructor(readonly url: string) {
    FakeEventSource.instances.push(this);
  }

  addEventListener(
    type: string,
    listener: (event: MessageEvent<string>) => void
  ) {
    this.listeners.set(type, [...(this.listeners.get(type) ?? []), listener]);
  }

  emit(type: string, data: unknown) {
    const event = { data: JSON.stringify(data) } as MessageEvent<string>;
    for (const listener of this.listeners.get(type) ?? []) {
      listener(event);
    }
  }

  emitInvalid(type: string) {
    const event = { data: "not-json" } as MessageEvent<string>;
    for (const listener of this.listeners.get(type) ?? []) {
      listener(event);
    }
  }

  close() {
    this.closed = true;
  }
}

describe("dashboard REST client", () => {
  it("applies API base URL from environment", () => {
    expect(
      getApiBaseUrl({ NEXT_PUBLIC_API_BASE_URL: "http://backend.local/" })
    ).toBe("http://backend.local");
    expect(
      getSseUrl({ NEXT_PUBLIC_API_BASE_URL: "http://backend.local" })
    ).toBe("http://backend.local/api/dashboard/stream");
    expect(getSseUrl({ NEXT_PUBLIC_SSE_URL: "http://sse.local/stream" })).toBe(
      "http://sse.local/stream"
    );
  });

  it("hydrates dashboard data from initial REST responses", async () => {
    const requested: string[] = [];
    const fetcher = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      requested.push(url);
      return jsonResponse(restPayloadFor(url));
    });

    const data = await fetchDashboardData(
      fetcher as unknown as typeof fetch,
      "http://api.local"
    );

    expect(requested).toContain("http://api.local/api/health");
    expect(requested).toContain("http://api.local/api/dashboard/summary");
    expect(requested).toContain(
      "http://api.local/api/dashboard/candles?symbol=BTCUSDT&interval=1m&limit=60"
    );
    expect(data.summary.environment).toBe("test");
    expect(data.summary.symbols[0]?.connection_state).toBe("CONNECTED");
    expect(data.candles).toHaveLength(2);
    expect(data.source_mix).toEqual([
      { source: "websocket", count: 1 },
      { source: "rest_backfill", count: 1 }
    ]);
  });
});

describe("dashboard SSE stream adapter", () => {
  it("receives snapshot, heartbeat, and error events", () => {
    FakeEventSource.instances = [];
    const statuses: StreamConnectionStatus[] = [];
    const snapshots: DashboardStreamPayload[] = [];
    const heartbeats: DashboardHeartbeatPayload[] = [];
    const errors: string[] = [];

    connectDashboardStream({
      url: "http://api.local/api/dashboard/stream",
      eventSourceFactory: FakeEventSource,
      handlers: {
        onConnectionChange: (status) => statuses.push(status),
        onSnapshot: (payload) => snapshots.push(payload),
        onHeartbeat: (payload) => heartbeats.push(payload),
        onStreamError: (message) => errors.push(message)
      }
    });
    const source = FakeEventSource.instances[0]!;
    source.onopen?.(new Event("open"));
    source.emit("dashboard_snapshot", streamSnapshot("LIVE"));
    source.emit("heartbeat", {
      event_type: "heartbeat",
      emitted_at: "2026-07-14T01:18:35Z"
    });
    source.emit("error", {
      event_type: "error",
      emitted_at: "2026-07-14T01:18:36Z",
      message: "dashboard snapshot failed"
    });

    expect(statuses).toEqual(["CONNECTING", "LIVE", "LIVE", "ERROR"]);
    expect(snapshots[0]?.system_health).toBe("LIVE");
    expect(heartbeats[0]?.emitted_at).toBe("2026-07-14T01:18:35Z");
    expect(errors).toContain("dashboard snapshot failed");
  });

  it("shows reconnecting on transport close and returns live after reconnect", () => {
    FakeEventSource.instances = [];
    const statuses: StreamConnectionStatus[] = [];
    const errors: string[] = [];

    connectDashboardStream({
      url: "http://api.local/api/dashboard/stream",
      eventSourceFactory: FakeEventSource,
      handlers: {
        onConnectionChange: (status) => statuses.push(status),
        onSnapshot: vi.fn(),
        onHeartbeat: vi.fn(),
        onStreamError: (message) => errors.push(message)
      }
    });
    const source = FakeEventSource.instances[0]!;
    source.onerror?.(new Event("error"));
    source.onopen?.(new Event("open"));

    expect(statuses).toEqual(["CONNECTING", "RECONNECTING", "LIVE"]);
    expect(errors[0]).toContain("재연결");
  });

  it("closes EventSource on unmount cleanup and does not duplicate sources", () => {
    FakeEventSource.instances = [];
    const stream = connectDashboardStream({
      url: "http://api.local/api/dashboard/stream",
      eventSourceFactory: FakeEventSource,
      handlers: {
        onConnectionChange: vi.fn(),
        onSnapshot: vi.fn(),
        onHeartbeat: vi.fn(),
        onStreamError: vi.fn()
      }
    });

    expect(FakeEventSource.instances).toHaveLength(1);
    stream.close();
    expect(FakeEventSource.instances[0]?.closed).toBe(true);
  });

  it("ignores invalid payloads safely", () => {
    FakeEventSource.instances = [];
    const snapshots: DashboardStreamPayload[] = [];
    const errors: string[] = [];

    connectDashboardStream({
      url: "http://api.local/api/dashboard/stream",
      eventSourceFactory: FakeEventSource,
      handlers: {
        onConnectionChange: vi.fn(),
        onSnapshot: (payload) => snapshots.push(payload),
        onHeartbeat: vi.fn(),
        onStreamError: (message) => errors.push(message)
      }
    });
    const source = FakeEventSource.instances[0]!;
    source.emitInvalid("dashboard_snapshot");

    expect(snapshots).toHaveLength(0);
    expect(errors).toContain("잘못된 대시보드 스냅샷을 무시했습니다.");
  });
});

describe("dashboard realtime state merge", () => {
  it("applies SSE snapshot updates while preserving last REST data", () => {
    const merged = mergeSnapshot(
      dashboardFixture,
      streamSnapshot("LIVE"),
      "LIVE"
    );

    expect(merged.summary.system_status).toBe("LIVE");
    expect(merged.summary.last_updated_at).toBe("2026-07-14T01:19:00Z");
    expect(merged.summary.symbols[0]?.connection_state).toBe("CONNECTED");
    expect(merged.candles).toEqual(dashboardFixture.candles);
    expect(merged.events).toEqual(dashboardFixture.events);
  });

  it("marks symbol connection as reconnecting when stream is not live", () => {
    const merged = mergeSnapshot(
      dashboardFixture,
      streamSnapshot("DEGRADED"),
      "RECONNECTING"
    );

    expect(
      merged.summary.symbols.map((symbol) => symbol.connection_state)
    ).toEqual(["RECONNECTING", "RECONNECTING"]);
  });
});

function jsonResponse(body: unknown) {
  return {
    ok: true,
    status: 200,
    json: async () => body
  };
}

function restPayloadFor(url: string): unknown {
  if (url.endsWith("/api/health")) {
    return {
      status: "ok",
      environment: "test",
      symbols: ["BTCUSDT", "ETHUSDT"],
      interval: "1m",
      initial_backfill_hours: 24
    };
  }
  if (url.endsWith("/api/dashboard/summary")) {
    return {
      system_status: "LIVE",
      symbols: [
        {
          symbol: "BTCUSDT",
          interval: "1m",
          status: "LIVE",
          last_event_at: "2026-07-14T01:18:00Z",
          last_candle_open_time: "2026-07-14T01:18:00Z",
          freshness_seconds: 3,
          lag_seconds: 1,
          latest_price: "118420.55"
        },
        {
          symbol: "ETHUSDT",
          interval: "1m",
          status: "STALE",
          last_event_at: "2026-07-14T01:10:00Z",
          last_candle_open_time: "2026-07-14T01:10:00Z",
          freshness_seconds: 480,
          lag_seconds: 480,
          latest_price: "3628.15"
        }
      ],
      total_missing_candle_count: 0,
      active_gap_count: 0,
      recent_backfill_job_count: 0,
      recent_event_count: 0
    };
  }
  if (url.includes("/api/dashboard/candles?symbol=BTCUSDT")) {
    return {
      symbol: "BTCUSDT",
      interval: "1m",
      candles: [
        {
          symbol: "BTCUSDT",
          interval: "1m",
          open_time: "2026-07-14T01:18:00Z",
          close_price: "118420.55",
          source: "websocket"
        }
      ]
    };
  }
  if (url.includes("/api/dashboard/candles?symbol=ETHUSDT")) {
    return {
      symbol: "ETHUSDT",
      interval: "1m",
      candles: [
        {
          symbol: "ETHUSDT",
          interval: "1m",
          open_time: "2026-07-14T01:18:00Z",
          close_price: "3628.15",
          source: "rest_backfill"
        }
      ]
    };
  }
  if (url.includes("/api/dashboard/gaps")) {
    return { gaps: [], total_missing_candle_count: 0 };
  }
  if (url.includes("/api/dashboard/backfill-jobs")) {
    return { jobs: [] };
  }
  if (url.includes("/api/dashboard/events")) {
    return { events: [] };
  }
  throw new Error(`Unexpected test URL: ${url}`);
}

function streamSnapshot(systemHealth: DashboardStreamPayload["system_health"]) {
  return {
    event_type: "dashboard_snapshot",
    emitted_at: "2026-07-14T01:19:00Z",
    system_health: systemHealth,
    symbols: [
      {
        symbol: "BTCUSDT",
        interval: "1m",
        status: "LIVE",
        last_event_at: "2026-07-14T01:19:00Z",
        last_candle_open_time: "2026-07-14T01:19:00Z",
        freshness_seconds: 1,
        lag_seconds: 1,
        latest_price: "118500.00"
      },
      {
        symbol: "ETHUSDT",
        interval: "1m",
        status: systemHealth === "LIVE" ? "LIVE" : "DEGRADED",
        last_event_at: "2026-07-14T01:18:00Z",
        last_candle_open_time: "2026-07-14T01:18:00Z",
        freshness_seconds: 61,
        lag_seconds: 61,
        latest_price: "3630.00"
      }
    ],
    active_gap_count: systemHealth === "LIVE" ? 0 : 1,
    latest_backfill_status: "SUCCEEDED"
  } satisfies DashboardStreamPayload;
}
