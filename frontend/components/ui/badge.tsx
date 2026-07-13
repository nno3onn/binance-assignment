import type { ReactNode } from "react";

import type { Tone } from "@/lib/dashboard-view-model";

const toneClass: Record<Tone, string> = {
  neutral: "border-slate-300 bg-slate-50 text-slate-700",
  success: "border-emerald-300 bg-emerald-50 text-emerald-800",
  warning: "border-amber-300 bg-amber-50 text-amber-800",
  danger: "border-rose-300 bg-rose-50 text-rose-800",
  active: "border-sky-300 bg-sky-50 text-sky-800"
};

type BadgeProps = {
  children: ReactNode;
  tone?: Tone;
  label?: string;
};

export function Badge({ children, tone = "neutral", label }: BadgeProps) {
  return (
    <span
      aria-label={label}
      className={`inline-flex items-center rounded-full border px-2.5 py-1 text-xs font-semibold ${toneClass[tone]}`}
    >
      {children}
    </span>
  );
}
