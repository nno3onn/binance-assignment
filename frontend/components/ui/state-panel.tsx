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
  const isLoading = state === "loading";

  return (
    <div
      className={`rounded-lg border p-5 text-center shadow-sm ${stateClass[state]}`}
      role="status"
      aria-live="polite"
    >
      {isLoading ? (
        <div
          className="mx-auto mb-4 h-10 w-10 animate-spin rounded-full border-4 border-sky-200 border-t-sky-700"
          aria-hidden="true"
        />
      ) : null}
      <div className="text-sm font-semibold">{title}</div>
      <p className="mt-1 text-sm leading-6">{message}</p>
    </div>
  );
}
