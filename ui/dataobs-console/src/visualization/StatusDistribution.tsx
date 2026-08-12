export interface DistributionItem {
  id: string;
  label: string;
  count: number;
  symbol?: string;
}
export function StatusDistribution({
  items,
  label,
}: {
  items: readonly DistributionItem[];
  label: string;
}) {
  const total = items.reduce((s, x) => s + x.count, 0);
  return (
    <figure className="viz-distribution" aria-label={label}>
      <div className="viz-distribution__bar">
        {items.map((x) => (
          <span
            key={x.id}
            className={`viz-semantic-${x.id}`}
            style={{ flexGrow: x.count }}
            title={`${x.label}: ${x.count}`}
          />
        ))}
      </div>
      <figcaption>
        <ul>
          {items.map((x) => (
            <li key={x.id}>
              <span aria-hidden="true">{x.symbol ?? "■"}</span> {x.label}:{" "}
              <strong>{x.count}</strong>
              {total ? ` (${Math.round((x.count / total) * 100)}%)` : ""}
            </li>
          ))}
        </ul>
      </figcaption>
    </figure>
  );
}
