import {
  Axis,
  Chart,
  LineSeries,
  Position,
  ScaleType,
  Settings,
} from "@elastic/charts";
import "@elastic/charts/dist/theme_only_light.css";
import { boundedLabel } from "./accessibility";
import { formatObserved, formatTimestamp } from "./formatters";
import { evidenceLabels } from "./semantics";
import { visualizationLimits } from "./tokens";
import type {
  AnomalyEvidence,
  ChangeAnnotation,
  Threshold,
  TimeSeriesModel,
} from "./types";
export function TimeSeries({
  series,
  label,
  anomalies = [],
  changes = [],
  thresholds = [],
}: {
  series: readonly TimeSeriesModel[];
  label: string;
  anomalies?: readonly AnomalyEvidence[];
  changes?: readonly ChangeAnnotation[];
  thresholds?: readonly Threshold[];
}) {
  series.forEach((s) => {
    if (s.points.length > visualizationLimits.timeSeriesPointsPerSeries)
      throw new Error(
        `Series ${s.id} exceeds ${visualizationLimits.timeSeriesPointsPerSeries} point limit`,
      );
  });
  return (
    <figure className="viz-time-series">
      <div className="viz-chart" aria-hidden="true">
        <Chart>
          <Settings showLegend />
          <Axis id="time" position={Position.Bottom} />
          <Axis id="value" position={Position.Left} />
          {series.map((s) => (
            <LineSeries
              key={s.id}
              id={s.id}
              name={`${boundedLabel(s.label)} — ${evidenceLabels[s.points[0]?.kind ?? "measured"]}`}
              xScaleType={ScaleType.Time}
              yScaleType={ScaleType.Linear}
              xAccessor="time"
              yAccessors={["value"]}
              data={s.points.map((p) => ({ time: p.time, value: p.value }))}
            />
          ))}
        </Chart>
      </div>
      <figcaption>
        <strong>{label}</strong>
        <span>
          {" "}
          Missing observations render as gaps. Forecast evidence is labelled
          separately and never converted to measured evidence.
        </span>
        <details>
          <summary>Accessible data table</summary>
          <table>
            <thead>
              <tr>
                <th>Series</th>
                <th>Timestamp (UTC)</th>
                <th>Value</th>
                <th>Evidence</th>
              </tr>
            </thead>
            <tbody>
              {series.flatMap((s) =>
                s.points.map((p, i) => (
                  <tr key={`${s.id}-${i}`}>
                    <th>{s.label}</th>
                    <td>{formatTimestamp(p.time)}</td>
                    <td>{formatObserved(p.value, s.unit)}</td>
                    <td>
                      {evidenceLabels[p.kind]}
                      {p.expectedLower != null && p.expectedUpper != null
                        ? ` · Expected ${p.expectedLower}–${p.expectedUpper}`
                        : ""}
                    </td>
                  </tr>
                )),
              )}
            </tbody>
          </table>
        </details>
        {thresholds.length > 0 && (
          <p>
            Thresholds:{" "}
            {thresholds.map((t) => `${t.label} ${t.value}`).join(", ")}
          </p>
        )}
        {anomalies.length > 0 && (
          <ul aria-label="Anomaly evidence">
            {anomalies.map((a, i) => (
              <li key={`${a.time}-${i}`}>
                {formatTimestamp(a.time)} — Anomaly
                {a.score == null ? "" : ` score ${a.score}`}
                {a.detector ? ` · ${a.detector}` : ""}
                {a.reason ? ` · ${boundedLabel(a.reason)}` : ""}
              </li>
            ))}
          </ul>
        )}
        {changes.length > 0 && (
          <ul aria-label="Change annotations">
            {changes.map((c) => (
              <li key={c.id}>
                {formatTimestamp(c.time)} — {c.kind}: {boundedLabel(c.label)}.
                Temporal proximity does not imply causality.
              </li>
            ))}
          </ul>
        )}
      </figcaption>
    </figure>
  );
}
