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
            title="실시간 연결 상태가 불안정합니다."
            message={`${streamError} 마지막 정상 데이터는 계속 표시됩니다.`}
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
            시장 데이터 파이프라인
          </p>
          <h1 className="text-xl font-semibold text-slate-950 sm:text-2xl">
            {APP_NAME}
          </h1>
        </div>
        <dl className="grid grid-cols-2 gap-3 text-sm sm:min-w-[34rem] sm:grid-cols-4">
          <div>
            <dt className="text-slate-500">환경</dt>
            <dd className="font-medium text-slate-950">{environment}</dd>
          </div>
          <div>
            <dt className="text-slate-500">마지막 갱신</dt>
            <dd className="font-medium text-slate-950">
              {formatUtc(lastUpdatedAt)}
            </dd>
          </div>
          <div>
            <dt className="text-slate-500">SSE</dt>
            <dd className="font-medium text-slate-950">
              {connectionStatusLabel(connectionStatus)}
            </dd>
          </div>
          <div>
            <dt className="text-slate-500">마지막 정상 수신</dt>
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
      title="시스템 상태 요약"
      description="파이프라인, 심볼, 서비스 상태를 한눈에 확인합니다."
    >
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
        <MetricCard
          label="전체 상태"
          value={runtimeStatusLabel(data.summary.system_status)}
          detail={`활성 누락 ${data.summary.active_gap_count}건`}
        >
          <StatusBadge status={data.summary.system_status} />
        </MetricCard>
        <MetricCard
          label="BTCUSDT"
          value={btc ? runtimeStatusLabel(btc.status) : "초기화 중"}
          detail={btc ? freshnessLabel(btc) : "수집 상태 없음"}
        >
          {btc ? <StatusBadge status={btc.status} /> : null}
        </MetricCard>
        <MetricCard
          label="ETHUSDT"
          value={eth ? runtimeStatusLabel(eth.status) : "초기화 중"}
          detail={eth ? freshnessLabel(eth) : "수집 상태 없음"}
        >
          {eth ? <StatusBadge status={eth.status} /> : null}
        </MetricCard>
        {data.summary.health_checks.map((check) => (
          <MetricCard
            key={check.name}
            label={check.name}
            value={serviceStatusLabel(check.status)}
            detail={check.detail}
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
          <Card key={symbol.symbol} className="p-4">
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
      <Card>
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
      <Card>
        {gaps.length === 0 ? (
          <div className="p-4">
            <StatePanel
              state="empty"
              title="활성 누락이 없습니다."
              message="모니터링 중인 심볼의 1분봉 시퀀스가 정상입니다."
            />
          </div>
        ) : (
          <DataTable
            headers={["심볼", "누락 시작", "누락 종료", "누락 캔들 수"]}
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
      title="백필 작업 이력"
      description="초기 백필과 재시작 복구 작업입니다."
    >
      <Card className="divide-y divide-slate-100">
        {jobs.map((job) => (
          <div key={job.id} className="p-4">
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
      title="최근 캔들 차트"
      description="시장 데이터 연속성을 확인하기 위한 최근 캔들입니다."
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
              name={`${selectedSymbol} 종가`}
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
      title="최근 이벤트"
      description="수집, 백필, 복구 과정에서 발생한 운영 이벤트입니다."
    >
      <Card>
        <DataTable headers={["발생 시각", "심각도", "이벤트 유형", "메시지"]}>
          {events.map((event) => (
            <tr key={event.id}>
              <TableCell>{formatUtc(event.event_time)}</TableCell>
              <TableCell>
                <SeverityBadge severity={event.severity} />
              </TableCell>
              <TableCell className="font-medium text-slate-950">
                {eventTypeLabel(event.event_type)}
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
    <Section
      title="데이터 수집 경로"
      description="저장된 캔들의 수집 경로 비율입니다."
    >
      <Card className="p-4">
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
