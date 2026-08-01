import { useCallback, useEffect, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import {
  incidentRuntimeApi,
  type CorrelationGroup,
  type EventStorm,
} from "../../api/incidentRuntime";
import { useProductContext } from "../../state/context";

function useScope() {
  const context = useProductContext();
  return { tenant: context.tenant, environment: context.environment };
}
export function EventStormInventory() {
  const { tenant, environment } = useScope();
  const [params, setParams] = useSearchParams();
  const [items, setItems] = useState<EventStorm[]>([]);
  const [status, setStatus] = useState("Loading event storms…");
  const load = useCallback(
    (signal?: AbortSignal) => {
      incidentRuntimeApi
        .storms(tenant, environment, params, signal)
        .then((r) => {
          setItems(r.items);
          setStatus(
            r.items.length
              ? `${r.items.length} event storms loaded`
              : "No event storms match these filters",
          );
        })
        .catch((e) => {
          if (e.name !== "AbortError")
            setStatus("Event storms are temporarily unavailable");
        });
    },
    [tenant, environment, params],
  );
  useEffect(() => {
    const controller = new AbortController();
    load(controller.signal);
    return () => controller.abort();
  }, [load]);
  return (
    <main>
      <header className="page-header">
        <div>
          <p className="eyebrow">Incidents</p>
          <h1>Event Storms</h1>
          <p>
            Durable flood-control windows and provider-neutral notification
            intent.
          </p>
        </div>
        <button onClick={() => load()}>Refresh</button>
      </header>
      <form aria-label="Event storm filters">
        <label>
          State{" "}
          <select
            value={params.get("state") || ""}
            onChange={(e) => {
              const next = new URLSearchParams(params);
              if (e.target.value) next.set("state", e.target.value);
              else next.delete("state");
              next.delete("cursor");
              setParams(next);
            }}
          >
            <option value="">All states</option>
            <option value="flooding">Flooding</option>
            <option value="recovering">Recovering</option>
            <option value="closed">Closed</option>
          </select>
        </label>
      </form>
      <p role="status" aria-live="polite">
        {status}
      </p>
      {items.length > 0 && (
        <div className="table-scroll">
          <table>
            <caption>Event storm inventory</caption>
            <thead>
              <tr>
                <th>State</th>
                <th>Representative</th>
                <th>Severity</th>
                <th>Rate</th>
                <th>Incidents</th>
                <th>Occurrences</th>
                <th>Assets</th>
                <th>Suppressed</th>
                <th>Decision</th>
                <th>Observed</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.flood_id}>
                  <td>
                    <Link
                      to={`/incidents/event-storms/${encodeURIComponent(item.flood_id)}`}
                    >
                      {item.state}
                    </Link>
                  </td>
                  <td>{item.representative_incident_id}</td>
                  <td>{item.highest_severity}</td>
                  <td>{item.event_rate}</td>
                  <td>{item.incident_count}</td>
                  <td>{item.occurrence_count}</td>
                  <td>{item.unique_assets}</td>
                  <td>{item.suppressed_notification_count}</td>
                  <td>{item.notification_decision}</td>
                  <td>{item.last_observed_at || "Unavailable"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </main>
  );
}
export function EventStormDetail() {
  const { floodId = "" } = useParams();
  const { tenant, environment } = useScope();
  const [storm, setStorm] = useState<EventStorm>();
  const [timeline, setTimeline] = useState<
    {
      event_id: string;
      timestamp: string;
      state: string;
      action: string;
      reason_codes: string[];
    }[]
  >([]);
  useEffect(() => {
    const c = new AbortController();
    Promise.all([
      incidentRuntimeApi.storm(tenant, environment, floodId, c.signal),
      incidentRuntimeApi.timeline(tenant, environment, floodId, c.signal),
    ]).then(([s, t]) => {
      setStorm(s);
      setTimeline(t.items);
    });
    return () => c.abort();
  }, [tenant, environment, floodId]);
  if (!storm) return <p role="status">Loading event storm…</p>;
  return (
    <main>
      <h1>Event Storm {storm.flood_id}</h1>
      <p>
        <strong>State:</strong> {storm.state}.{" "}
        <strong>Notification intent:</strong> {storm.notification_decision};
        provider delivery has not been attempted.
      </p>
      <dl>
        <dt>Representative incident</dt>
        <dd>{storm.representative_incident_id}</dd>
        <dt>Observed events</dt>
        <dd>{storm.event_count}</dd>
        <dt>Suppressed notifications</dt>
        <dd>{storm.suppressed_notification_count}</dd>
      </dl>
      <h2>Timeline</h2>
      <table>
        <thead>
          <tr>
            <th>Time</th>
            <th>State</th>
            <th>Action</th>
            <th>Reasons</th>
          </tr>
        </thead>
        <tbody>
          {timeline.map((e) => (
            <tr key={e.event_id}>
              <td>{e.timestamp}</td>
              <td>{e.state}</td>
              <td>{e.action}</td>
              <td>{e.reason_codes.join(", ")}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </main>
  );
}
export function CorrelationGroupDetail() {
  const { groupId = "" } = useParams();
  const { tenant, environment } = useScope();
  const [group, setGroup] = useState<CorrelationGroup>();
  useEffect(() => {
    const c = new AbortController();
    incidentRuntimeApi
      .group(tenant, environment, groupId, c.signal)
      .then(setGroup);
    return () => c.abort();
  }, [tenant, environment, groupId]);
  if (!group) return <p role="status">Loading correlation group…</p>;
  return (
    <main>
      <h1>Correlation Group {group.group_id}</h1>
      <p>{group.wording}</p>
      <dl>
        <dt>Representative</dt>
        <dd>{group.representative_incident_id}</dd>
        <dt>Members</dt>
        <dd>
          {group.member_count}
          {group.members_truncated ? " (sample truncated)" : ""}
        </dd>
        <dt>Confidence</dt>
        <dd>{group.confidence}</dd>
        <dt>Evidence coverage</dt>
        <dd>{group.evidence_coverage}</dd>
        <dt>Policy</dt>
        <dd>
          {group.policy_name} {group.policy_version} ({group.policy_hash})
        </dd>
        <dt>Flood state</dt>
        <dd>{group.flood_state}</dd>
      </dl>
      <h2>Bounded member sample</h2>
      <ul>
        {group.member_sample.map((id) => (
          <li key={id}>
            <Link to={`/incidents/${encodeURIComponent(id)}`}>{id}</Link>
          </li>
        ))}
      </ul>
      <h2>Decision explanation</h2>
      <p>{group.reason_codes.join(", ")}</p>
    </main>
  );
}
