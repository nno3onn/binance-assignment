import type { ReactNode } from "react";

type CardProps = {
  children: ReactNode;
  className?: string;
};

export function Card({ children, className = "" }: CardProps) {
  return (
    <div
      className={`rounded-lg border border-slate-200 bg-white shadow-sm ${className}`}
    >
      {children}
    </div>
  );
}

type MetricCardProps = {
  label: string;
  value: string;
  detail?: string;
  children?: ReactNode;
};

export function MetricCard({
  label,
  value,
  detail,
  children
}: MetricCardProps) {
  return (
    <Card className="p-4">
      <div className="text-xs font-medium uppercase tracking-wide text-slate-500">
        {label}
      </div>
      <div className="mt-2 text-2xl font-semibold text-slate-950">{value}</div>
      {detail ? <p className="mt-1 text-sm text-slate-600">{detail}</p> : null}
      {children ? <div className="mt-3">{children}</div> : null}
    </Card>
  );
}
