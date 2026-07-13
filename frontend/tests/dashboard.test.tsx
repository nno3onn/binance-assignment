import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import HomePage from "@/app/page";
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
  sourceMixPercentages,
  statusTone
} from "@/lib/dashboard-view-model";

describe("operations dashboard layout", () => {
  it("renders the dashboard page", () => {
    const markup = renderToStaticMarkup(<HomePage />);

    expect(markup).toContain("Market Data Operations Console");
    expect(markup).toContain("Environment");
    expect(markup).toContain("Last Updated");
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
      expect(markup).toContain(`Status ${status}`);
      expect(markup).toContain(status);
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
});
