"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";

import { fetchDashboardData, getApiBaseUrl, getSseUrl } from "./dashboard-api";
import { connectDashboardStream } from "./dashboard-stream";
import type {
  DashboardData,
  DashboardStreamPayload,
  StreamConnectionStatus,
  SymbolStatus
} from "./dashboard-types";

export const dashboardQueryKey = ["dashboard", "snapshot"] as const;

export type DashboardRealtimeState = {
  data: DashboardData | undefined;
  isLoading: boolean;
  isEmpty: boolean;
  apiError: Error | null;
  streamError: string | null;
  connectionStatus: StreamConnectionStatus;
  lastGoodUpdateAt: string | null;
  lastHeartbeatAt: string | null;
};

export function useDashboardRealtime(): DashboardRealtimeState {
  const queryClient = useQueryClient();
  const [connectionStatus, setConnectionStatus] =
    useState<StreamConnectionStatus>("CONNECTING");
  const [streamError, setStreamError] = useState<string | null>(null);
  const [lastHeartbeatAt, setLastHeartbeatAt] = useState<string | null>(null);
  const [lastGoodUpdateAt, setLastGoodUpdateAt] = useState<string | null>(null);
  const apiBaseUrl = useMemo(() => getApiBaseUrl(), []);
  const sseUrl = useMemo(() => getSseUrl(), []);

  const query = useQuery({
    queryKey: dashboardQueryKey,
    queryFn: () => fetchDashboardData(fetch, apiBaseUrl),
    staleTime: Infinity,
    refetchOnWindowFocus: false
  });

  useEffect(() => {
    const stream = connectDashboardStream({
      url: sseUrl,
      handlers: {
        onConnectionChange: setConnectionStatus,
        onHeartbeat: (payload) => {
          setLastHeartbeatAt(payload.emitted_at);
        },
        onSnapshot: (payload) => {
          setStreamError(null);
          setLastGoodUpdateAt(payload.emitted_at);
          queryClient.setQueryData<DashboardData>(
            dashboardQueryKey,
            (current) =>
              current ? mergeSnapshot(current, payload, "LIVE") : current
          );
        },
        onStreamError: setStreamError
      }
    });

    return () => {
      stream.close();
    };
  }, [queryClient, sseUrl]);

  const data = query.data;
  return {
    data,
    isLoading: query.isLoading && data === undefined,
    isEmpty:
      !query.isLoading &&
      data !== undefined &&
      data.summary.symbols.length === 0 &&
      data.events.length === 0,
    apiError: query.error instanceof Error ? query.error : null,
    streamError,
    connectionStatus,
    lastGoodUpdateAt: lastGoodUpdateAt ?? data?.summary.last_updated_at ?? null,
    lastHeartbeatAt
  };
}

export function mergeSnapshot(
  current: DashboardData,
  payload: DashboardStreamPayload,
  connectionStatus: StreamConnectionStatus
): DashboardData {
  return {
    ...current,
    summary: {
      ...current.summary,
      system_status: payload.system_health,
      active_gap_count: payload.active_gap_count,
      last_updated_at: payload.emitted_at,
      symbols: payload.symbols.map((symbol) => ({
        ...symbol,
        connection_state: toSymbolConnectionState(
          symbol.status,
          connectionStatus
        )
      }))
    },
    backfill_jobs: current.backfill_jobs.map((job, index) =>
      index === 0 && payload.latest_backfill_status !== null
        ? { ...job, status: payload.latest_backfill_status }
        : job
    )
  };
}

function toSymbolConnectionState(
  status: Omit<SymbolStatus, "connection_state">["status"],
  connectionStatus: StreamConnectionStatus
): SymbolStatus["connection_state"] {
  if (connectionStatus === "LIVE" && status === "LIVE") {
    return "CONNECTED";
  }
  if (connectionStatus === "DISCONNECTED" || connectionStatus === "ERROR") {
    return "DISCONNECTED";
  }
  return "RECONNECTING";
}
