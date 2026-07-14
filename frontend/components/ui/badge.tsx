import type { ReactNode } from "react";

import type { Tone } from "@/lib/dashboard-view-model";

const toneClass: Record<Tone, string> = {
  neutral: "border-slate-300 bg-slate-50 text-slate-700",
  success: "border-teal-300 bg-teal-50 text-teal-900",
  warning: "border-amber-300 bg-amber-50 text-amber-900",
  danger: "border-rose-300 bg-rose-50 text-rose-900",
  active: "border-sky-300 bg-sky-50 text-sky-900"
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
      className={`inline-flex max-w-full items-center rounded-full border px-2.5 py-1 text-xs font-semibold leading-none ${toneClass[tone]}`}
    >
      {children}
    </span>
  );
}
