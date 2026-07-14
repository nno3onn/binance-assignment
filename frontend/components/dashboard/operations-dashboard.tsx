"use client";

import { useState } from "react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from "recharts";

import { Badge } from "@/components/ui/badge";
import { Card, MetricCard } from "@/components/ui/card";
import { DataTable, TableCell } from "@/components/ui/data-table";
import { Section } from "@/components/ui/section";
import { StatePanel } from "@/components/ui/state-panel";
import { APP_NAME } from "@/lib/project";
import type {
  ApplicationEvent,
  BackfillJob,
  DashboardData,
  EventSeverity,
  Gap,
  StreamConnectionStatus,
  SymbolStatus
} from "@/lib/dashboard-types";
import {
  chartSeries,
  formatDuration,
  formatPrice,
  formatUtc,
  freshnessLabel,
  sourceMixPercentages,
  statusTone
} from "@/lib/dashboard-view-model";

type OperationsDashboardProps = {
  data: DashboardData;
  connectionStatus?: StreamConnectionStatus;
  lastGoodUpdateAt?: string | null;
  lastHeartbeatAt?: string | null;
  streamError?: string | null;
};

const symbols: Array<SymbolStatus["symbol"]> = ["BTCUSDT", "ETHUSDT"];

export function OperationsDashboard({
  data,
  connectionStatus = "DISCONNECTED",
  lastGoodUpdateAt = null,
  lastHeartbeatAt = null,
  streamError = null
}: OperationsDashboardProps) {
  const [selectedSymbol, setSelectedSymbol] =
    useState<SymbolStatus["symbol"]>("BTCUSDT");
  const series = chartSeries(data, selectedSymbol);

  return (
    <main className="min-h-screen bg-slate-100">
      <TopBar
        environment={data.summary.environment}
        lastUpdatedAt={data.summary.last_updated_at}
        connectionStatus={connectionStatus}
        lastGoodUpdateAt={lastGoodUpdateAt}
      />
      <div className="mx-auto grid w-full max-w-7xl gap-6 px-4 py-6 sm:px-6 lg:px-8">
        {streamError ? (
          <StatePanel
            state="error"
            title="Realtime stream degraded"
            message={`${streamError} Last good update is still displayed.`}
          />
        ) : null}
        <SystemHealthSummary
          data={data}
          connectionStatus={connectionStatus}
          lastHeartbeatAt={lastHeartbeatAt}
        />

        <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_360px]">
          <DataFreshness symbols={data.summary.symbols} />
          <SourceMix data={data} />
        </div>

        <SymbolPipelineStatus symbols={data.summary.symbols} />

        <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_420px]">
          <GapDetector gaps={data.gaps} />
          <BackfillTimeline jobs={data.backfill_jobs} />
        </div>

        <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_420px]">
          <RecentCandleChart
            selectedSymbol={selectedSymbol}
            onSelectSymbol={setSelectedSymbol}
            series={series}
          />
          <RecentEventLog events={data.events} />
        </div>
      </div>
    </main>
  );
}

function TopBar({
  environment,
  lastUpdatedAt,
  connectionStatus,
  lastGoodUpdateAt
}: {
  environment: string;
  lastUpdatedAt: string;
  connectionStatus: StreamConnectionStatus;
  lastGoodUpdateAt: string | null;
}) {
  return (
    <header className="border-b border-slate-200 bg-white">
      <div className="mx-auto flex w-full max-w-7xl flex-col gap-3 px-4 py-4 sm:flex-row sm:items-center sm:justify-between sm:px-6 lg:px-8">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Market data pipeline
          </p>
          <h1 className="text-xl font-semibold text-slate-950 sm:text-2xl">
            {APP_NAME}
          </h1>
        </div>
        <dl className="grid grid-cols-2 gap-3 text-sm sm:min-w-[34rem] sm:grid-cols-4">
          <div>
            <dt className="text-slate-500">Environment</dt>
            <dd className="font-medium text-slate-950">{environment}</dd>
          </div>
          <div>
            <dt className="text-slate-500">Last Updated</dt>
            <dd className="font-medium text-slate-950">
              {formatUtc(lastUpdatedAt)}
            </dd>
          </div>
          <div>
            <dt className="text-slate-500">SSE</dt>
            <dd className="font-medium text-slate-950">{connectionStatus}</dd>
          </div>
          <div>
            <dt className="text-slate-500">Last Good</dt>
            <dd className="font-medium text-slate-950">
              {formatUtc(lastGoodUpdateAt)}
            </dd>
          </div>
        </dl>
      </div>
    </header>
  );
}

function SystemHealthSummary({
  data,
  connectionStatus,
  lastHeartbeatAt
}: OperationsDashboardProps) {
  const btc = data.summary.symbols.find(
    (symbol) => symbol.symbol === "BTCUSDT"
  );
  const eth = data.summary.symbols.find(
    (symbol) => symbol.symbol === "ETHUSDT"
  );

  return (
    <Section
      title="System Health Summary"
      description="Pipeline state, symbol health, and service checks."
    >
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
        <MetricCard
          label="Overall"
          value={data.summary.system_status}
          detail={`${data.summary.active_gap_count} active gaps`}
        >
          <StatusBadge status={data.summary.system_status} />
        </MetricCard>
        <MetricCard
          label="BTCUSDT"
          value={btc?.status ?? "INITIALIZING"}
          detail={btc ? freshnessLabel(btc) : "No runtime status"}
        >
          {btc ? <StatusBadge status={btc.status} /> : null}
        </MetricCard>
        <MetricCard
          label="ETHUSDT"
          value={eth?.status ?? "INITIALIZING"}
          detail={eth ? freshnessLabel(eth) : "No runtime status"}
        >
          {eth ? <StatusBadge status={eth.status} /> : null}
        </MetricCard>
        {data.summary.health_checks.map((check) => (
          <MetricCard
            key={check.name}
            label={check.name}
            value={check.status}
            detail={check.detail}
          >
            <Badge
              tone={statusTone[check.status]}
              label={`${check.name} ${check.status}`}
            >
              {check.status}
            </Badge>
          </MetricCard>
        ))}
        <MetricCard
          label="SSE Stream"
          value={connectionStatus ?? "DISCONNECTED"}
          detail={`Heartbeat ${formatUtc(lastHeartbeatAt ?? null)}`}
        >
          <ConnectionBadge status={connectionStatus ?? "DISCONNECTED"} />
        </MetricCard>
      </div>
    </Section>
  );
}

function DataFreshness({
  symbols: symbolStatuses
}: {
  symbols: SymbolStatus[];
}) {
  return (
    <Section title="Data Freshness" description="Last event and lag by symbol.">
      <div className="grid gap-3 md:grid-cols-2">
        {symbolStatuses.map((symbol) => (
          <Card key={symbol.symbol} className="p-4">
            <div className="flex items-start justify-between gap-3">
              <div>
                <h3 className="text-sm font-semibold text-slate-950">
                  {symbol.symbol}
                </h3>
                <p className="mt-1 text-sm text-slate-600">
                  Last event {formatUtc(symbol.last_event_at)}
                </p>
              </div>
              <StatusBadge status={symbol.status} />
            </div>
            <dl className="mt-4 grid grid-cols-2 gap-3 text-sm">
              <div>
                <dt className="text-slate-500">Freshness</dt>
                <dd className="font-semibold text-slate-950">
                  {formatDuration(symbol.freshness_seconds)}
                </dd>
              </div>
              <div>
                <dt className="text-slate-500">Lag</dt>
                <dd className="font-semibold text-slate-950">
                  {formatDuration(symbol.lag_seconds)}
                </dd>
              </div>
            </dl>
          </Card>
        ))}
      </div>
    </Section>
  );
}

function SymbolPipelineStatus({
  symbols: symbolStatuses
}: {
  symbols: SymbolStatus[];
}) {
  return (
    <Section
      title="Symbol Pipeline Status"
      description="Runtime status from collector through persistence."
    >
      <Card>
        <DataTable
          headers={[
            "Symbol",
            "Status",
            "Latest Price",
            "Last Event",
            "Freshness",
            "Connection State"
          ]}
        >
          {symbolStatuses.map((symbol) => (
            <tr key={symbol.symbol}>
              <TableCell className="font-semibold text-slate-950">
                {symbol.symbol}
              </TableCell>
              <TableCell>
                <StatusBadge status={symbol.status} />
              </TableCell>
              <TableCell>{formatPrice(symbol.latest_price)}</TableCell>
              <TableCell>{formatUtc(symbol.last_event_at)}</TableCell>
              <TableCell>{formatDuration(symbol.freshness_seconds)}</TableCell>
              <TableCell>{symbol.connection_state}</TableCell>
            </tr>
          ))}
        </DataTable>
      </Card>
    </Section>
  );
}

function GapDetector({ gaps }: { gaps: Gap[] }) {
  return (
    <Section
      title="Gap Detector"
      description="Missing 1m candle ranges that require recovery."
    >
      <Card>
        {gaps.length === 0 ? (
          <div className="p-4">
            <StatePanel
              state="empty"
              title="No active gaps"
              message="Expected 1m candle sequence is complete for monitored symbols."
            />
          </div>
        ) : (
          <DataTable
            headers={["Symbol", "Gap Start", "Gap End", "Missing Candles"]}
          >
            {gaps.map((gap) => (
              <tr key={`${gap.symbol}-${gap.start_time}`}>
                <TableCell className="font-semibold">{gap.symbol}</TableCell>
                <TableCell>{formatUtc(gap.start_time)}</TableCell>
                <TableCell>{formatUtc(gap.end_time)}</TableCell>
                <TableCell>{gap.missing_candle_count}</TableCell>
              </tr>
            ))}
          </DataTable>
        )}
      </Card>
    </Section>
  );
}

function BackfillTimeline({ jobs }: { jobs: BackfillJob[] }) {
  return (
    <Section
      title="Backfill Job Timeline"
      description="Initial backfills and restart recovery jobs."
    >
      <Card className="divide-y divide-slate-100">
        {jobs.map((job) => (
          <div key={job.id} className="p-4">
            <div className="flex items-start justify-between gap-3">
              <div>
                <h3 className="text-sm font-semibold text-slate-950">
                  {job.symbol} / {job.job_type}
                </h3>
                <p className="mt-1 text-sm text-slate-600">
                  {formatUtc(job.range_start)} to {formatUtc(job.range_end)}
                </p>
              </div>
              <BackfillBadge status={job.status} />
            </div>
            <dl className="mt-3 grid grid-cols-2 gap-3 text-sm">
              <div>
                <dt className="text-slate-500">Recovered</dt>
                <dd className="font-semibold text-slate-950">
                  {job.inserted_candle_count + job.updated_candle_count}/
                  {job.requested_candle_count}
                </dd>
              </div>
              <div>
                <dt className="text-slate-500">Completed</dt>
                <dd className="font-semibold text-slate-950">
                  {formatUtc(job.finished_at)}
                </dd>
              </div>
            </dl>
          </div>
        ))}
      </Card>
    </Section>
  );
}

function RecentCandleChart({
  selectedSymbol,
  onSelectSymbol,
  series
}: {
  selectedSymbol: SymbolStatus["symbol"];
  onSelectSymbol: (symbol: SymbolStatus["symbol"]) => void;
  series: Array<{ time: string; close: number }>;
}) {
  return (
    <Section
      title="Recent Candle Chart"
      description="Recent REST candles used as market-data continuity context."
      action={
        <div className="inline-flex rounded-lg border border-slate-200 bg-white p-1">
          {symbols.map((symbol) => (
            <button
              key={symbol}
              type="button"
              onClick={() => onSelectSymbol(symbol)}
              className={`rounded-md px-3 py-1.5 text-sm font-medium ${
                selectedSymbol === symbol
                  ? "bg-slate-900 text-white"
                  : "text-slate-600 hover:bg-slate-100"
              }`}
              aria-pressed={selectedSymbol === symbol}
            >
              {symbol}
            </button>
          ))}
        </div>
      }
    >
      <Card className="h-80 p-4">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart
            data={series}
            margin={{ top: 8, right: 16, bottom: 8, left: 0 }}
          >
            <defs>
              <linearGradient id="closePrice" x1="0" x2="0" y1="0" y2="1">
                <stop offset="5%" stopColor="#0f766e" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#0f766e" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid stroke="#e2e8f0" strokeDasharray="3 3" />
            <XAxis dataKey="time" tickLine={false} axisLine={false} />
            <YAxis
              tickLine={false}
              axisLine={false}
              domain={["dataMin", "dataMax"]}
              width={70}
            />
            <Tooltip />
            <Area
              dataKey="close"
              type="monotone"
              stroke="#0f766e"
              fill="url(#closePrice)"
              strokeWidth={2}
              name={`${selectedSymbol} close`}
            />
          </AreaChart>
        </ResponsiveContainer>
      </Card>
    </Section>
  );
}

function RecentEventLog({ events }: { events: ApplicationEvent[] }) {
  return (
    <Section
      title="Recent Event Log"
      description="Operational events from collection, backfill, and recovery."
    >
      <Card>
        <DataTable
          headers={["Occurred At", "Severity", "Event Type", "Message"]}
        >
          {events.map((event) => (
            <tr key={event.id}>
              <TableCell>{formatUtc(event.event_time)}</TableCell>
              <TableCell>
                <SeverityBadge severity={event.severity} />
              </TableCell>
              <TableCell className="font-medium text-slate-950">
                {event.event_type}
              </TableCell>
              <TableCell>{event.message}</TableCell>
            </tr>
          ))}
        </DataTable>
      </Card>
    </Section>
  );
}

function SourceMix({ data }: OperationsDashboardProps) {
  const mix = sourceMixPercentages(data);
  return (
    <Section title="Source Mix" description="Stored candle source lineage.">
      <Card className="p-4">
        <div className="space-y-4">
          {mix.map((item) => (
            <div key={item.source}>
              <div className="flex items-center justify-between text-sm">
                <span className="font-medium text-slate-950">
                  {item.source}
                </span>
                <span className="text-slate-600">
                  {item.percentage}% / {item.count}
                </span>
              </div>
              <div className="mt-2 h-2 rounded-full bg-slate-100">
                <div
                  className="h-2 rounded-full bg-teal-700"
                  style={{ width: `${item.percentage}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      </Card>
    </Section>
  );
}

export function StatusBadge({ status }: { status: SymbolStatus["status"] }) {
  return (
    <Badge tone={statusTone[status]} label={`Status ${status}`}>
      {status}
    </Badge>
  );
}

function BackfillBadge({ status }: { status: BackfillJob["status"] }) {
  const tone =
    status === "SUCCEEDED"
      ? "success"
      : status === "FAILED"
        ? "danger"
        : "active";
  return (
    <Badge tone={tone} label={`Backfill ${status}`}>
      {status}
    </Badge>
  );
}

function ConnectionBadge({ status }: { status: StreamConnectionStatus }) {
  const tone =
    status === "LIVE"
      ? "success"
      : status === "ERROR" || status === "DISCONNECTED"
        ? "danger"
        : "warning";
  return (
    <Badge tone={tone} label={`SSE connection ${status}`}>
      {status}
    </Badge>
  );
}

function SeverityBadge({ severity }: { severity: EventSeverity }) {
  const tone =
    severity === "ERROR"
      ? "danger"
      : severity === "WARNING"
        ? "warning"
        : "neutral";
  return (
    <Badge tone={tone} label={`Severity ${severity}`}>
      {severity}
    </Badge>
  );
}
