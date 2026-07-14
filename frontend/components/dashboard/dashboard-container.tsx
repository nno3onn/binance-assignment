"use client";

import { OperationsDashboard } from "@/components/dashboard/operations-dashboard";
import { StatePanel } from "@/components/ui/state-panel";
import { useDashboardRealtime } from "@/lib/dashboard-realtime";

export function DashboardContainer() {
  const state = useDashboardRealtime();

  if (state.isLoading) {
    return (
      <main className="min-h-screen bg-slate-100 p-6">
        <StatePanel
          state="loading"
          title="Loading dashboard"
          message="Fetching the initial REST snapshot from the backend."
        />
      </main>
    );
  }

  if (state.apiError && state.data === undefined) {
    return (
      <main className="min-h-screen bg-slate-100 p-6">
        <StatePanel
          state="error"
          title="Dashboard unavailable"
          message={state.apiError.message}
        />
      </main>
    );
  }

  if (state.isEmpty || state.data === undefined) {
    return (
      <main className="min-h-screen bg-slate-100 p-6">
        <StatePanel
          state="empty"
          title="No dashboard data"
          message="Backend responded, but no runtime status, candles, jobs, or events are available yet."
        />
      </main>
    );
  }

  return (
    <OperationsDashboard
      data={state.data}
      connectionStatus={state.connectionStatus}
      lastGoodUpdateAt={state.lastGoodUpdateAt}
      lastHeartbeatAt={state.lastHeartbeatAt}
      streamError={state.streamError}
    />
  );
}
