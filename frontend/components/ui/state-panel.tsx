type StatePanelProps = {
  title: string;
  message: string;
  state: "loading" | "empty" | "error";
};

const stateClass: Record<StatePanelProps["state"], string> = {
  loading: "border-sky-200 bg-sky-50 text-sky-900",
  empty: "border-slate-200 bg-slate-50 text-slate-700",
  error: "border-rose-200 bg-rose-50 text-rose-900"
};

export function StatePanel({ title, message, state }: StatePanelProps) {
  return (
    <div className={`rounded-lg border p-4 ${stateClass[state]}`} role="status">
      <div className="text-sm font-semibold">{title}</div>
      <p className="mt-1 text-sm">{message}</p>
    </div>
  );
}
