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
          title="대시보드를 불러오는 중입니다."
          message="백엔드에서 초기 데이터를 불러오는 중입니다."
        />
      </main>
    );
  }

  if (state.apiError && state.data === undefined) {
    return (
      <main className="min-h-screen bg-slate-100 p-6">
        <StatePanel
          state="error"
          title="대시보드를 사용할 수 없습니다."
          message={`초기 데이터를 불러오지 못했습니다. ${state.apiError.message}`}
        />
      </main>
    );
  }

  if (state.isEmpty || state.data === undefined) {
    return (
      <main className="min-h-screen bg-slate-100 p-6">
        <StatePanel
          state="empty"
          title="데이터가 없습니다."
          message="백엔드는 응답했지만 아직 수집 상태, 캔들, 작업, 이벤트 데이터가 없습니다."
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
