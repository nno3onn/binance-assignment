import type { ReactNode } from "react";

type CardProps = {
  children: ReactNode;
  className?: string;
};

export function Card({ children, className = "" }: CardProps) {
  return (
    <div
      className={`rounded-lg border border-slate-200/80 bg-white shadow-sm shadow-slate-200/60 ${className}`}
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
  className?: string;
};

export function MetricCard({
  label,
  value,
  detail,
  children,
  className = ""
}: MetricCardProps) {
  return (
    <Card className={`p-4 ${className}`}>
      <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
        {label}
      </div>
      <div className="mt-2 break-words text-2xl font-semibold leading-tight text-slate-950">
        {value}
      </div>
      {detail ? <p className="mt-1 text-sm text-slate-600">{detail}</p> : null}
      {children ? <div className="mt-3">{children}</div> : null}
    </Card>
  );
}
