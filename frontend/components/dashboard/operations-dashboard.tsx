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
  backfillJobTypeLabel,
  backfillStatusLabel,
  candleSourceLabel,
  connectionStatusLabel,
  eventTypeLabel,
  sourceMixPercentages,
  runtimeStatusLabel,
  serviceStatusLabel,
  severityLabel,
  symbolConnectionStatusLabel,
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
const EVENT_PAGE_SIZE = 5;

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
    <main className="min-h-screen bg-[#f4f7fb]">
      <TopBar
        environment={data.summary.environment}
        lastUpdatedAt={data.summary.last_updated_at}
        connectionStatus={connectionStatus}
        lastGoodUpdateAt={lastGoodUpdateAt}
      />
      <div className="mx-auto grid w-full max-w-7xl gap-5 px-4 py-5 sm:px-6 lg:gap-6 lg:px-8 lg:py-7">
        <IncidentStatusStrip
          data={data}
          connectionStatus={connectionStatus}
          lastGoodUpdateAt={lastGoodUpdateAt}
        />
        {streamError ? (
          <StatePanel
            state="error"
            title="실시간 연결 상태가 불안정합니다."
            message={`${streamError} 마지막 정상 데이터는 계속 표시됩니다.`}
          />
        ) : null}
        <SystemHealthSummary
          data={data}
          connectionStatus={connectionStatus}
          lastHeartbeatAt={lastHeartbeatAt}
        />

        <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_360px] lg:gap-6">
          <DataFreshness symbols={data.summary.symbols} />
          <SourceMix data={data} />
        </div>

        <SymbolPipelineStatus symbols={data.summary.symbols} />

        <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_420px] xl:gap-6">
          <GapDetector gaps={data.gaps} />
          <BackfillTimeline jobs={data.backfill_jobs} />
        </div>

        <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_420px] xl:gap-6">
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
    <header className="border-b border-teal-900/20 bg-gradient-to-r from-teal-950 via-teal-900 to-slate-950 text-white">
      <div className="h-1 bg-teal-400" />
      <div className="mx-auto flex w-full max-w-7xl flex-col gap-4 px-4 py-5 sm:px-6 lg:flex-row lg:items-center lg:justify-between lg:px-8">
        <div className="min-w-0">
          <p className="text-xs font-semibold uppercase tracking-wide text-teal-200">
            시장 데이터 파이프라인
          </p>
          <h1 className="mt-1 text-2xl font-semibold tracking-tight text-white sm:text-3xl">
            {APP_NAME}
          </h1>
        </div>
        <dl className="grid gap-2 text-sm sm:grid-cols-2 lg:min-w-[38rem] lg:grid-cols-4">
          <div className="rounded-lg border border-white/10 bg-white/10 px-3 py-2">
            <dt className="text-teal-100">환경</dt>
            <dd className="font-medium text-white">{environment}</dd>
          </div>
          <div className="rounded-lg border border-white/10 bg-white/10 px-3 py-2">
            <dt className="text-teal-100">마지막 갱신</dt>
            <dd className="font-medium text-white">
              {formatUtc(lastUpdatedAt)}
            </dd>
          </div>
          <div className="rounded-lg border border-white/10 bg-white/10 px-3 py-2">
            <dt className="text-teal-100">SSE</dt>
            <dd className="font-medium text-white">
              {connectionStatusLabel(connectionStatus)}
            </dd>
          </div>
          <div className="rounded-lg border border-white/10 bg-white/10 px-3 py-2">
            <dt className="text-teal-100">마지막 정상 수신</dt>
            <dd className="font-medium text-white">
              {formatUtc(lastGoodUpdateAt)}
            </dd>
          </div>
        </dl>
      </div>
    </header>
  );
}

function IncidentStatusStrip({
  data,
  connectionStatus,
  lastGoodUpdateAt
}: {
  data: DashboardData;
  connectionStatus: StreamConnectionStatus;
  lastGoodUpdateAt: string | null;
}) {
  const degradedSymbols = data.summary.symbols.filter(
    (symbol) => symbol.status !== "LIVE"
  );
  const headline =
    data.summary.system_status === "LIVE"
      ? "현재 수집 파이프라인은 정상입니다."
      : "조치가 필요한 수집 상태가 있습니다.";
  const toneClass = incidentToneClass(data.summary.system_status);

  return (
    <section className="overflow-hidden rounded-lg border border-teal-900/10 bg-white shadow-md shadow-slate-200/70">
      <div className="grid gap-0 lg:grid-cols-[minmax(0,1.2fr)_repeat(3,minmax(0,1fr))]">
        <div className={`p-4 text-white sm:p-5 ${toneClass}`}>
          <div className="text-xs font-semibold uppercase tracking-wide text-teal-100">
            운영 상태
          </div>
          <div className="mt-2 text-xl font-semibold tracking-tight">
            {headline}
          </div>
          <p className="mt-1 text-sm text-teal-50">
            마지막 정상 수신 {formatUtc(lastGoodUpdateAt)}
          </p>
        </div>
        <StatusStripItem
          label="전체 상태"
          value={runtimeStatusLabel(data.summary.system_status)}
          detail={`SSE ${connectionStatusLabel(connectionStatus)}`}
          markerClass="bg-teal-700"
        />
        <StatusStripItem
          label="지연 심볼"
          value={`${degradedSymbols.length}개`}
          detail={
            degradedSymbols.length > 0
              ? degradedSymbols.map((symbol) => symbol.symbol).join(", ")
              : "모든 심볼 정상"
          }
          markerClass={
            degradedSymbols.length > 0 ? "bg-amber-500" : "bg-teal-600"
          }
        />
        <StatusStripItem
          label="활성 누락"
          value={`${data.summary.active_gap_count}건`}
          detail={`누락 캔들 ${data.summary.total_missing_candle_count}개`}
          markerClass={
            data.summary.active_gap_count > 0 ? "bg-rose-500" : "bg-teal-600"
          }
        />
      </div>
    </section>
  );
}

function incidentToneClass(status: SymbolStatus["status"]) {
  if (status === "ERROR") {
    return "bg-rose-800";
  }
  if (status === "DEGRADED" || status === "STALE") {
    return "bg-amber-700";
  }
  if (status === "BACKFILLING") {
    return "bg-sky-800";
  }
  return "bg-teal-800";
}

function StatusStripItem({
  label,
  value,
  detail,
  markerClass
}: {
  label: string;
  value: string;
  detail: string;
  markerClass: string;
}) {
  return (
    <div className="border-t border-slate-100 p-4 sm:p-5 lg:border-l lg:border-t-0">
      <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
        <span className={`h-2 w-2 rounded-full ${markerClass}`} />
        <span>{label}</span>
      </div>
      <div className="mt-2 text-2xl font-semibold tracking-tight text-slate-950">
        {value}
      </div>
      <p className="mt-1 text-sm text-slate-600">{detail}</p>
    </div>
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
      title="시스템 상태 요약"
      description="파이프라인, 심볼, 서비스 상태를 한눈에 확인합니다."
    >
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-6">
        <MetricCard
          label="전체 상태"
          value={runtimeStatusLabel(data.summary.system_status)}
          detail={`활성 누락 ${data.summary.active_gap_count}건`}
          className="border-l-4 border-l-teal-700 xl:col-span-2"
        >
          <StatusBadge status={data.summary.system_status} />
        </MetricCard>
        <MetricCard
          label="BTCUSDT"
          value={btc ? runtimeStatusLabel(btc.status) : "초기화 중"}
          detail={btc ? freshnessLabel(btc) : "수집 상태 없음"}
          className="border-l-4 border-l-emerald-500"
        >
          {btc ? <StatusBadge status={btc.status} /> : null}
        </MetricCard>
        <MetricCard
          label="ETHUSDT"
          value={eth ? runtimeStatusLabel(eth.status) : "초기화 중"}
          detail={eth ? freshnessLabel(eth) : "수집 상태 없음"}
          className="border-l-4 border-l-amber-500"
        >
          {eth ? <StatusBadge status={eth.status} /> : null}
        </MetricCard>
        {data.summary.health_checks.map((check) => (
          <MetricCard
            key={check.name}
            label={check.name}
            value={serviceStatusLabel(check.status)}
            detail={check.detail}
            className="border-l-4 border-l-slate-300"
          >
            <Badge
              tone={statusTone[check.status]}
              label={`${check.name} ${serviceStatusLabel(check.status)}`}
            >
              {serviceStatusLabel(check.status)}
            </Badge>
          </MetricCard>
        ))}
        <MetricCard
          label="SSE 스트림"
          value={connectionStatusLabel(connectionStatus ?? "DISCONNECTED")}
          detail={`하트비트 ${formatUtc(lastHeartbeatAt ?? null)}`}
          className="border-l-4 border-l-teal-500"
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
    <Section
      title="데이터 최신성"
      description="심볼별 마지막 이벤트와 지연 시간입니다."
    >
      <div className="grid gap-3 md:grid-cols-2">
        {symbolStatuses.map((symbol) => (
          <Card
            key={symbol.symbol}
            className={`p-4 ${symbolCardClass(symbol.status)}`}
          >
            <div className="flex items-start justify-between gap-3">
              <div>
                <h3 className="text-sm font-semibold text-slate-950">
                  {symbol.symbol}
                </h3>
                <p className="mt-1 text-sm text-slate-600">
                  마지막 이벤트 {formatUtc(symbol.last_event_at)}
                </p>
              </div>
              <StatusBadge status={symbol.status} />
            </div>
            <dl className="mt-4 grid grid-cols-2 gap-3 text-sm">
              <div>
                <dt className="text-slate-500">최신성</dt>
                <dd className="font-semibold text-slate-950">
                  {formatDuration(symbol.freshness_seconds)}
                </dd>
              </div>
              <div>
                <dt className="text-slate-500">지연</dt>
                <dd className="font-semibold text-slate-950">
                  {formatDuration(symbol.lag_seconds)}
                </dd>
              </div>
            </dl>
            <div className="mt-4 h-2 rounded-full bg-slate-100">
              <div
                className="h-2 rounded-full bg-teal-700"
                style={{
                  width: `${Math.max(
                    8,
                    Math.min(100, 100 - (symbol.lag_seconds ?? 100) / 6)
                  )}%`
                }}
              />
            </div>
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
      title="심볼별 파이프라인 상태"
      description="수집기부터 저장소까지의 런타임 상태입니다."
    >
      <div className="grid gap-3 md:hidden">
        {symbolStatuses.map((symbol) => (
          <Card key={symbol.symbol} className="p-4">
            <div className="flex items-start justify-between gap-3">
              <div>
                <h3 className="text-base font-semibold text-slate-950">
                  {symbol.symbol}
                </h3>
                <p className="mt-1 text-sm text-slate-600">
                  {formatPrice(symbol.latest_price)}
                </p>
              </div>
              <StatusBadge status={symbol.status} />
            </div>
            <dl className="mt-4 grid grid-cols-2 gap-3 text-sm">
              <div>
                <dt className="text-slate-500">마지막 이벤트</dt>
                <dd className="mt-1 font-medium text-slate-950">
                  {formatUtc(symbol.last_event_at)}
                </dd>
              </div>
              <div>
                <dt className="text-slate-500">연결 상태</dt>
                <dd className="mt-1 font-medium text-slate-950">
                  {symbolConnectionStatusLabel(symbol.connection_state)}
                </dd>
              </div>
              <div>
                <dt className="text-slate-500">최신성</dt>
                <dd className="mt-1 font-medium text-slate-950">
                  {formatDuration(symbol.freshness_seconds)}
                </dd>
              </div>
              <div>
                <dt className="text-slate-500">지연</dt>
                <dd className="mt-1 font-medium text-slate-950">
                  {formatDuration(symbol.lag_seconds)}
                </dd>
              </div>
            </dl>
          </Card>
        ))}
      </div>
      <Card className="hidden overflow-hidden md:block">
        <DataTable
          headers={[
            "심볼",
            "상태",
            "최신 가격",
            "마지막 이벤트",
            "최신성",
            "연결 상태"
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
              <TableCell>
                {symbolConnectionStatusLabel(symbol.connection_state)}
              </TableCell>
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
      title="누락 데이터 현황"
      description="복구가 필요한 1분봉 누락 구간입니다."
    >
      <Card className="overflow-hidden">
        {gaps.length === 0 ? (
          <div className="p-4">
            <StatePanel
              state="empty"
              title="활성 누락이 없습니다."
              message="모니터링 중인 심볼의 1분봉 시퀀스가 정상입니다."
            />
          </div>
        ) : (
          <>
            <div className="grid gap-3 p-4 md:hidden">
              {gaps.map((gap) => (
                <div
                  key={`${gap.symbol}-${gap.start_time}-card`}
                  className="rounded-lg border border-rose-100 bg-rose-50/60 p-3"
                >
                  <div className="flex items-center justify-between gap-3">
                    <div className="font-semibold text-slate-950">
                      {gap.symbol}
                    </div>
                    <Badge tone="danger" label="누락 캔들">
                      {gap.missing_candle_count}개 누락
                    </Badge>
                  </div>
                  <dl className="mt-3 grid gap-2 text-sm">
                    <div>
                      <dt className="text-slate-500">누락 시작</dt>
                      <dd className="font-medium text-slate-950">
                        {formatUtc(gap.start_time)}
                      </dd>
                    </div>
                    <div>
                      <dt className="text-slate-500">누락 종료</dt>
                      <dd className="font-medium text-slate-950">
                        {formatUtc(gap.end_time)}
                      </dd>
                    </div>
                  </dl>
                </div>
              ))}
            </div>
            <div className="hidden md:block">
              <DataTable
                headers={["심볼", "누락 시작", "누락 종료", "누락 캔들 수"]}
              >
                {gaps.map((gap) => (
                  <tr key={`${gap.symbol}-${gap.start_time}`}>
                    <TableCell className="font-semibold">
                      {gap.symbol}
                    </TableCell>
                    <TableCell>{formatUtc(gap.start_time)}</TableCell>
                    <TableCell>{formatUtc(gap.end_time)}</TableCell>
                    <TableCell>{gap.missing_candle_count}</TableCell>
                  </tr>
                ))}
              </DataTable>
            </div>
          </>
        )}
      </Card>
    </Section>
  );
}

function BackfillTimeline({ jobs }: { jobs: BackfillJob[] }) {
  return (
    <Section
      title="백필 작업 이력"
      description="초기 백필과 재시작 복구 작업입니다."
    >
      <Card className="divide-y divide-slate-100 overflow-hidden">
        {jobs.length === 0 ? (
          <div className="p-4">
            <StatePanel
              state="empty"
              title="백필 작업이 없습니다."
              message="아직 기록된 초기 백필 또는 복구 작업이 없습니다."
            />
          </div>
        ) : (
          jobs.map((job) => (
            <div key={job.id} className="relative p-4 pl-6">
              <div className="absolute left-0 top-0 h-full w-1 bg-teal-100" />
              <div className="absolute left-0 top-5 h-3 w-1 bg-teal-700" />
              <div className="flex items-start justify-between gap-3">
                <div>
                  <h3 className="text-sm font-semibold text-slate-950">
                    {job.symbol} / {backfillJobTypeLabel(job.job_type)}
                  </h3>
                  <p className="mt-1 text-sm text-slate-600">
                    {formatUtc(job.range_start)} ~ {formatUtc(job.range_end)}
                  </p>
                </div>
                <BackfillBadge status={job.status} />
              </div>
              <dl className="mt-3 grid grid-cols-2 gap-3 text-sm">
                <div>
                  <dt className="text-slate-500">복구됨</dt>
                  <dd className="font-semibold text-slate-950">
                    {job.inserted_candle_count + job.updated_candle_count}/
                    {job.requested_candle_count}
                  </dd>
                </div>
                <div>
                  <dt className="text-slate-500">완료 시각</dt>
                  <dd className="font-semibold text-slate-950">
                    {formatUtc(job.finished_at)}
                  </dd>
                </div>
              </dl>
            </div>
          ))
        )}
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
  const latestClose = series.at(-1)?.close;
  return (
    <Section
      title="최근 캔들 차트"
      description="시장 데이터 연속성을 확인하기 위한 최근 캔들입니다."
      action={
        <div className="inline-flex rounded-lg border border-teal-100 bg-white p-1 shadow-sm">
          {symbols.map((symbol) => (
            <button
              key={symbol}
              type="button"
              onClick={() => onSelectSymbol(symbol)}
              className={`rounded-md px-3 py-1.5 text-sm font-medium ${
                selectedSymbol === symbol
                  ? "bg-teal-800 text-white"
                  : "text-slate-600 hover:bg-teal-50 hover:text-teal-900"
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
        {series.length === 0 ? (
          <StatePanel
            state="empty"
            title="캔들 데이터가 없습니다."
            message="선택한 심볼의 최근 캔들이 아직 저장되지 않았습니다."
          />
        ) : (
          <div className="flex h-full flex-col">
            <div className="mb-3 flex items-center justify-between gap-3">
              <div>
                <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                  최신 캔들
                </div>
                <div className="mt-1 text-lg font-semibold text-slate-950">
                  {latestClose !== undefined
                    ? formatPrice(String(latestClose))
                    : "캔들 없음"}
                </div>
              </div>
              <Badge tone="success" label="선택 심볼">
                {selectedSymbol}
              </Badge>
            </div>
            <div className="min-h-0 flex-1">
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
                  <Tooltip
                    contentStyle={{
                      borderRadius: 8,
                      borderColor: "#cbd5e1",
                      boxShadow: "0 10px 24px rgba(15, 23, 42, 0.12)"
                    }}
                  />
                  <Area
                    dataKey="close"
                    type="monotone"
                    stroke="#0f766e"
                    fill="url(#closePrice)"
                    strokeWidth={2}
                    name={`${selectedSymbol} 종가`}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}
      </Card>
    </Section>
  );
}

function RecentEventLog({ events }: { events: ApplicationEvent[] }) {
  const [visibleCount, setVisibleCount] = useState(EVENT_PAGE_SIZE);
  const visibleEvents = events.slice(0, visibleCount);
  const hiddenCount = Math.max(events.length - visibleCount, 0);
  const nextCount = Math.min(EVENT_PAGE_SIZE, hiddenCount);

  return (
    <Section
      title="최근 이벤트"
      description="수집, 백필, 복구 과정에서 발생한 운영 이벤트입니다."
    >
      <Card className="overflow-hidden">
        {events.length === 0 ? (
          <div className="p-4">
            <StatePanel
              state="empty"
              title="이벤트가 없습니다."
              message="아직 기록된 운영 이벤트가 없습니다."
            />
          </div>
        ) : (
          <>
            <div className="divide-y divide-slate-100">
              {visibleEvents.map((event) => (
                <div key={event.id} className="relative p-4 pl-10">
                  <div className="absolute left-5 top-0 h-full w-px bg-slate-200" />
                  <div
                    className={`absolute left-[15px] top-5 h-3 w-3 rounded-full border-2 border-white shadow-sm ${severityDotClass(
                      event.severity
                    )}`}
                  />
                  <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <SeverityBadge severity={event.severity} />
                        <h3 className="text-sm font-semibold text-slate-950">
                          {eventTypeLabel(event.event_type)}
                        </h3>
                      </div>
                      <p className="mt-2 text-sm leading-6 text-slate-700">
                        {event.message}
                      </p>
                    </div>
                    <time className="shrink-0 text-xs font-medium text-slate-500">
                      {formatUtc(event.event_time)}
                    </time>
                  </div>
                </div>
              ))}
            </div>
            {hiddenCount > 0 ? (
              <div className="border-t border-slate-100 bg-slate-50/70 p-3">
                <button
                  type="button"
                  className="w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-700 shadow-sm transition hover:border-teal-500 hover:text-teal-800 focus:outline-none focus:ring-2 focus:ring-teal-500 focus:ring-offset-2"
                  onClick={() =>
                    setVisibleCount((current) => current + EVENT_PAGE_SIZE)
                  }
                >
                  더보기 {nextCount}개
                </button>
              </div>
            ) : null}
          </>
        )}
      </Card>
    </Section>
  );
}

function SourceMix({ data }: OperationsDashboardProps) {
  const mix = sourceMixPercentages(data);
  return (
    <Section
      title="데이터 수집 경로"
      description="저장된 캔들의 수집 경로 비율입니다."
    >
      <Card className="p-4">
        {mix.length === 0 ? (
          <StatePanel
            state="empty"
            title="수집 경로 데이터가 없습니다."
            message="저장된 캔들이 생기면 경로 비율이 표시됩니다."
          />
        ) : (
          <div className="space-y-4">
            {mix.map((item) => (
              <div key={item.source}>
                <div className="flex items-center justify-between text-sm">
                  <span className="font-medium text-slate-950">
                    {candleSourceLabel(item.source)}
                  </span>
                  <span className="text-slate-600">
                    {item.percentage}% / {item.count}
                  </span>
                </div>
                <div className="mt-2 h-2 rounded-full bg-slate-100">
                  <div
                    className={`h-2 rounded-full ${sourceBarClass(
                      item.source
                    )}`}
                    style={{ width: `${item.percentage}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>
    </Section>
  );
}

function symbolCardClass(status: SymbolStatus["status"]) {
  if (status === "LIVE") {
    return "border-l-4 border-l-teal-600";
  }
  if (status === "ERROR") {
    return "border-l-4 border-l-rose-500";
  }
  if (status === "BACKFILLING") {
    return "border-l-4 border-l-sky-500";
  }
  return "border-l-4 border-l-amber-500";
}

function severityDotClass(severity: EventSeverity) {
  if (severity === "ERROR") {
    return "bg-rose-600";
  }
  if (severity === "WARNING") {
    return "bg-amber-500";
  }
  return "bg-teal-700";
}

function sourceBarClass(source: string) {
  return source === "websocket" ? "bg-teal-700" : "bg-sky-600";
}

export function StatusBadge({ status }: { status: SymbolStatus["status"] }) {
  return (
    <Badge
      tone={statusTone[status]}
      label={`상태 ${runtimeStatusLabel(status)}`}
    >
      {runtimeStatusLabel(status)}
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
    <Badge tone={tone} label={`백필 ${backfillStatusLabel(status)}`}>
      {backfillStatusLabel(status)}
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
    <Badge tone={tone} label={`SSE 연결 ${connectionStatusLabel(status)}`}>
      {connectionStatusLabel(status)}
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
    <Badge tone={tone} label={`심각도 ${severityLabel(severity)}`}>
      {severityLabel(severity)}
    </Badge>
  );
}
