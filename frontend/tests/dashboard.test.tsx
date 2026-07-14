import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

import {
  OperationsDashboard,
  StatusBadge
} from "@/components/dashboard/operations-dashboard";
import { StatePanel } from "@/components/ui/state-panel";
import { dashboardFixture } from "@/lib/dashboard-fixture";
import type { RuntimeStatus } from "@/lib/dashboard-types";
import {
  chartSeries,
  dashboardSectionNames,
  runtimeStatusLabel,
  sourceMixPercentages,
  statusTone
} from "@/lib/dashboard-view-model";

describe("operations dashboard layout", () => {
  it("renders the dashboard shell", () => {
    const markup = renderToStaticMarkup(
      <OperationsDashboard
        data={dashboardFixture}
        connectionStatus="LIVE"
        lastGoodUpdateAt="2026-07-14T01:18:30Z"
        lastHeartbeatAt="2026-07-14T01:18:32Z"
      />
    );

    expect(markup).toContain("시장 데이터 운영 대시보드");
    expect(markup).toContain("환경");
    expect(markup).toContain("마지막 갱신");
    expect(markup).toContain("SSE");
    expect(markup).toContain("연결됨");
  });

  it("renders all required operational sections", () => {
    const markup = renderToStaticMarkup(
      <OperationsDashboard data={dashboardFixture} />
    );

    for (const section of dashboardSectionNames()) {
      expect(markup).toContain(section);
    }
  });

  it("renders every runtime status badge with text labels", () => {
    const statuses: RuntimeStatus[] = [
      "INITIALIZING",
      "LIVE",
      "DEGRADED",
      "BACKFILLING",
      "STALE",
      "ERROR"
    ];
    const markup = renderToStaticMarkup(
      <>
        {statuses.map((status) => (
          <StatusBadge key={status} status={status} />
        ))}
      </>
    );

    for (const status of statuses) {
      expect(markup).toContain(`상태 ${runtimeStatusLabel(status)}`);
      expect(markup).toContain(runtimeStatusLabel(status));
      expect(statusTone[status]).toBeDefined();
    }
  });

  it("renders loading, empty, and error states", () => {
    const markup = renderToStaticMarkup(
      <>
        <StatePanel
          state="loading"
          title="Loading dashboard"
          message="Waiting for snapshot."
        />
        <StatePanel
          state="empty"
          title="No active gaps"
          message="Expected sequence is complete."
        />
        <StatePanel
          state="error"
          title="Dashboard unavailable"
          message="Snapshot query failed."
        />
      </>
    );

    expect(markup).toContain("Loading dashboard");
    expect(markup).toContain("No active gaps");
    expect(markup).toContain("Dashboard unavailable");
  });

  it("supports fixture-based symbol chart switching", () => {
    const btc = chartSeries(dashboardFixture, "BTCUSDT");
    const eth = chartSeries(dashboardFixture, "ETHUSDT");

    expect(btc).toHaveLength(6);
    expect(eth).toHaveLength(6);
    expect(btc[0]?.close).not.toEqual(eth[0]?.close);
  });

  it("uses responsive grid structure and source mix percentages", () => {
    const markup = renderToStaticMarkup(
      <OperationsDashboard data={dashboardFixture} />
    );
    const mix = sourceMixPercentages(dashboardFixture);

    expect(markup).toContain("sm:grid-cols-2");
    expect(markup).toContain("xl:grid-cols");
    expect(mix.reduce((sum, item) => sum + item.percentage, 0)).toBe(100);
  });

  it("does not import fixture data from the production page", () => {
    const pageSource = readFileSync(
      path.join(process.cwd(), "app/page.tsx"),
      "utf8"
    );

    expect(pageSource).toContain("DashboardContainer");
    expect(pageSource).not.toContain("dashboardFixture");
    expect(pageSource).not.toContain("dashboard-fixture");
  });
});
