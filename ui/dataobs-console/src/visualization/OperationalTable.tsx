import { useState } from "react";
export interface OperationalColumn<T> {
  id: string;
  label: string;
  render: (row: T) => React.ReactNode;
  sortValue?: (row: T) => string | number | null;
}
export function OperationalTable<T extends { id: string }>({
  rows,
  columns,
  caption,
  pageSize = 25,
  serverOrdered = false,
}: {
  rows: readonly T[];
  columns: readonly OperationalColumn<T>[];
  caption: string;
  pageSize?: number;
  serverOrdered?: boolean;
}) {
  const [page, setPage] = useState(0),
    [sort, setSort] = useState<string>();
  const col = columns.find((c) => c.id === sort);
  const data =
    !serverOrdered && col?.sortValue
      ? [...rows].sort((a, b) =>
          String(col.sortValue!(a) ?? "").localeCompare(
            String(col.sortValue!(b) ?? ""),
            undefined,
            { numeric: true },
          ),
        )
      : rows;
  const pages = Math.max(1, Math.ceil(data.length / pageSize)),
    shown = data.slice(page * pageSize, (page + 1) * pageSize);
  return (
    <div className="viz-table-scroll">
      <table className="viz-operational-table">
        <caption>{caption}</caption>
        <thead>
          <tr>
            {columns.map((c) => (
              <th key={c.id} scope="col">
                {c.sortValue && !serverOrdered ? (
                  <button
                    onClick={() => {
                      setSort(c.id);
                      setPage(0);
                    }}
                    aria-sort={sort === c.id ? "ascending" : undefined}
                  >
                    {c.label}
                  </button>
                ) : (
                  c.label
                )}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {shown.map((r) => (
            <tr key={r.id}>
              {columns.map((c) => (
                <td key={c.id}>{c.render(r)}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      <nav aria-label={`${caption} pagination`}>
        <button disabled={page === 0} onClick={() => setPage((p) => p - 1)}>
          Previous
        </button>{" "}
        Page {page + 1} of {pages}{" "}
        <button
          disabled={page + 1 >= pages}
          onClick={() => setPage((p) => p + 1)}
        >
          Next
        </button>
      </nav>
    </div>
  );
}
