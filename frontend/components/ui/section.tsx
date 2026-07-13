import type { ReactNode } from "react";

type SectionProps = {
  title: string;
  description?: string;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
};

export function Section({
  title,
  description,
  action,
  children,
  className = ""
}: SectionProps) {
  return (
    <section className={className} aria-labelledby={titleToId(title)}>
      <div className="mb-3 flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h2
            id={titleToId(title)}
            className="text-base font-semibold text-slate-950"
          >
            {title}
          </h2>
          {description ? (
            <p className="mt-1 text-sm text-slate-600">{description}</p>
          ) : null}
        </div>
        {action}
      </div>
      {children}
    </section>
  );
}

function titleToId(title: string) {
  return title.toLowerCase().replaceAll(" ", "-");
}
