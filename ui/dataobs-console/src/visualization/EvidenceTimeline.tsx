import { formatTimestamp } from "./formatters";
import type { ChangeKind, EvidenceAvailability } from "./types";
export interface TimelineEvent {
  id: string;
  time: number;
  lane:
    | "anomaly"
    | "quality"
    | "run"
    | "change"
    | "incident"
    | "workflow"
    | "remediation";
  title: string;
  source: string;
  availability?: EvidenceAvailability;
  changeKind?: ChangeKind;
  detail?: string;
}
export function EvidenceTimeline({
  events,
  label,
  onSelect,
}: {
  events: readonly TimelineEvent[];
  label: string;
  onSelect?: (event: TimelineEvent) => void;
}) {
  return (
    <section className="viz-timeline" aria-label={label}>
      <p className="viz-disclaimer">
        Events share a time axis; proximity does not establish causation.
      </p>
      <ol>
        {[...events]
          .sort((a, b) => a.time - b.time)
          .map((e) => (
            <li key={e.id} className={`viz-timeline__${e.lane}`}>
              <button onClick={() => onSelect?.(e)}>
                <span className="viz-timeline__marker" aria-hidden="true" />
                <time dateTime={new Date(e.time).toISOString()}>
                  {formatTimestamp(e.time)}
                </time>
                <strong>{e.title}</strong>
                <small>
                  {e.lane} · Source: {e.source} ·{" "}
                  {e.availability ?? "available"}
                </small>
                {e.detail && <span>{e.detail}</span>}
              </button>
            </li>
          ))}
      </ol>
    </section>
  );
}
