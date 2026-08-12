import type { HealthState } from "./types";
import { healthLabels } from "./semantics";
export interface MatrixCell {
  row: string;
  column: string;
  state: HealthState;
  detail?: string;
}
export function HealthMatrix({
  rows,
  columns,
  cells,
  label,
}: {
  rows: readonly string[];
  columns: readonly string[];
  cells: readonly MatrixCell[];
  label: string;
}) {
  const find = (r: string, c: string) =>
    cells.find((x) => x.row === r && x.column === c);
  return (
    <div className="viz-table-scroll">
      <table className="viz-matrix">
        <caption>{label}</caption>
        <thead>
          <tr>
            <th scope="col">Entity</th>
            {columns.map((c) => (
              <th scope="col" key={c}>
                {c}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r}>
              <th scope="row">{r}</th>
              {columns.map((c) => {
                const x = find(r, c);
                return (
                  <td
                    key={c}
                    tabIndex={0}
                    className={`viz-health-${x?.state ?? "unknown"}`}
                    title={x?.detail}
                  >
                    <span aria-hidden="true">
                      {x?.state === "healthy"
                        ? "✓"
                        : x?.state === "warning"
                          ? "!"
                          : x?.state === "critical"
                            ? "×"
                            : "?"}
                    </span>
                    <span className="sr-only">
                      {healthLabels[x?.state ?? "unknown"]}
                    </span>
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
