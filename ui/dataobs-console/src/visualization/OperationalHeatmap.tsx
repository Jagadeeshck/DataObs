export interface HeatmapCell {
  row: string;
  column: string;
  value: number | null;
}
export function OperationalHeatmap({
  rows,
  columns,
  cells,
  label,
  unit,
}: {
  rows: readonly string[];
  columns: readonly string[];
  cells: readonly HeatmapCell[];
  label: string;
  unit: string;
}) {
  const vals = cells.flatMap((x) => (x.value === null ? [] : [x.value])),
    max = Math.max(...vals, 1);
  return (
    <div className="viz-table-scroll">
      <table className="viz-heatmap">
        <caption>{label}</caption>
        <thead>
          <tr>
            <th>Dimension</th>
            {columns.map((c) => (
              <th key={c}>{c}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r}>
              <th scope="row">{r}</th>
              {columns.map((c) => {
                const x = cells.find((v) => v.row === r && v.column === c),
                  value = x?.value ?? null;
                return (
                  <td
                    key={c}
                    style={
                      value === null
                        ? undefined
                        : ({
                            "--viz-intensity": value / max,
                          } as React.CSSProperties)
                    }
                  >
                    {value === null ? "No observation" : `${value} ${unit}`}
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
