import type { ReactNode } from "react";

type DataTableProps = {
  headers: string[];
  children: ReactNode;
};

export function DataTable({ headers, children }: DataTableProps) {
  return (
    <div className="overflow-x-auto">
      <table className="min-w-full border-separate border-spacing-0 text-left text-sm">
        <thead>
          <tr>
            {headers.map((header) => (
              <th
                key={header}
                scope="col"
                className="border-b border-slate-200 bg-slate-50 px-3 py-2 text-xs font-semibold uppercase tracking-wide text-slate-500"
              >
                {header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">{children}</tbody>
      </table>
    </div>
  );
}

type TableCellProps = {
  children: ReactNode;
  className?: string;
};

export function TableCell({ children, className = "" }: TableCellProps) {
  return <td className={`px-3 py-3 align-top ${className}`}>{children}</td>;
}
