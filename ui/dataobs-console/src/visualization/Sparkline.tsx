import { trendSummary } from "./accessibility";
export function Sparkline({
  values,
  label,
  maxPoints = 50,
}: {
  values: readonly (number | null)[];
  label: string;
  maxPoints?: number;
}) {
  const data = values.slice(-maxPoints);
  const observed = data.filter((v): v is number => v !== null);
  const min = Math.min(...observed),
    max = Math.max(...observed),
    span = max - min || 1;
  let path = "";
  data.forEach((v, i) => {
    if (v === null) {
      path = "" + path;
      return;
    }
    const x = data.length === 1 ? 50 : (i / (data.length - 1)) * 100,
      y = 22 - ((v - min) / span) * 20;
    path += `${path.endsWith(" ") || !path ? "M" : " L"}${x} ${y}`;
  });
  return (
    <figure className="viz-sparkline">
      <svg
        viewBox="0 0 100 24"
        role="img"
        aria-label={`${label}. ${trendSummary(data)}`}
      >
        <path d={path} vectorEffect="non-scaling-stroke" />
      </svg>
      <figcaption className="sr-only">{trendSummary(data)}</figcaption>
    </figure>
  );
}
