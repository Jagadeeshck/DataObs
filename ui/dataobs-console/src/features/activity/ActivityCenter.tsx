import { useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { DataStatusBanner } from "../../components/Evidence";
import { WatchlistStore, contextFingerprint } from "../../dashboards/watchlist";
import { useProductContext, timeRangeBounds } from "../../state/context";
import { activityProviders } from "../../activity/registry";
import { loadActivity, type ActivityLoad } from "../../activity/controller";
import {
  ActivitySeenStore,
  activityContextFingerprint,
} from "../../activity/localState";
import { watchlistActivity } from "../../activity/watchlist";
import {
  activityInvestigationPath,
  activitySourcePath,
} from "../../activity/navigation";
import type { ActivityItem } from "../../activity/types";

type Tab = "all" | "attention" | "watchlist";
const empty: ActivityLoad = {
  items: [],
  providers: {},
  permissionLimited: false,
};
export function ActivityCenter() {
  const {
    tenant,
    environment,
    identity,
    timeRange,
    refreshGeneration,
    requestRefresh,
  } = useProductContext();
  const [load, setLoad] = useState(empty),
    [loading, setLoading] = useState(true),
    [tab, setTab] = useState<Tab>("all");
  const [capability, setCapability] = useState("all"),
    [severity, setSeverity] = useState("all"),
    [state, setState] = useState("all"),
    [evidence, setEvidence] = useState("all"),
    [seenFilter, setSeenFilter] = useState("all");
  const [selected, setSelected] = useState<ActivityItem>(),
    [seenGeneration, setSeenGeneration] = useState(0);
  const closeButton = useRef<HTMLButtonElement>(null);
  const fingerprint = activityContextFingerprint(tenant, environment),
    store = useMemo(() => new ActivitySeenStore(), []);
  useEffect(() => {
    if (!tenant || !environment) return;
    const controller = new AbortController();
    // eslint-disable-next-line react-hooks/set-state-in-effect -- a trusted context generation must synchronously hide stale activity
    setLoading(true);
    setLoad(empty);
    setSelected(undefined);
    const bounds = timeRangeBounds(timeRange);
    void loadActivity(
      activityProviders,
      {
        context: {
          tenant,
          environment,
          permissions: identity?.permissions ?? [],
        },
        ...bounds,
        maximumItems: 25,
      },
      controller.signal,
    )
      .then((value) => {
        if (!controller.signal.aborted) setLoad(value);
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort("context_changed");
  }, [
    tenant,
    environment,
    identity?.permissions,
    timeRange,
    refreshGeneration,
  ]);
  useEffect(() => {
    if (selected) closeButton.current?.focus();
  }, [selected]);
  const seen = new Set(store.read(fingerprint).map((x) => x.key));
  const watched = new WatchlistStore().read(
    contextFingerprint(tenant, environment),
  );
  const visible = load.items.filter((item) => {
    if (tab === "attention" && !item.attention) return false;
    if (tab === "watchlist" && !watchlistActivity([item], watched).length)
      return false;
    return (
      (capability === "all" || item.capabilityId === capability) &&
      (severity === "all" || item.severity === severity) &&
      (state === "all" || item.state === state) &&
      (evidence === "all" || item.evidenceState === evidence) &&
      (seenFilter === "all" || (seenFilter === "seen") === seen.has(item.key))
    );
  });
  const mark = (keys: string[]) => {
    store.mark(fingerprint, keys);
    setSeenGeneration((x) => x + 1);
  };
  void seenGeneration;
  const failed = Object.values(load.providers).some((x) => x !== "available");
  return (
    <section className="activity-center" aria-labelledby="activity-heading">
      <header>
        <div>
          <h1 id="activity-heading">Activity Center</h1>
          <p>
            Bounded operational activity. Seen state is local only and never
            acknowledges or changes operational state.
          </p>
        </div>
        <button onClick={requestRefresh}>Refresh activity</button>
      </header>
      <div role="tablist" aria-label="Activity views" className="activity-tabs">
        {(["all", "attention", "watchlist"] as Tab[]).map((value) => (
          <button
            key={value}
            role="tab"
            aria-selected={tab === value}
            onClick={() => setTab(value)}
          >
            {value === "all"
              ? "All Activity"
              : value === "attention"
                ? "Needs Attention"
                : "Watchlist"}
          </button>
        ))}
      </div>
      <div className="activity-filters" aria-label="Activity filters">
        <label>
          Capability
          <select
            value={capability}
            onChange={(e) => setCapability(e.target.value)}
          >
            <option value="all">All</option>
            <option value="incidents">Incidents</option>
          </select>
        </label>
        <label>
          Severity
          <select
            value={severity}
            onChange={(e) => setSeverity(e.target.value)}
          >
            <option value="all">All</option>
            {["critical", "high", "medium", "low", "unknown"].map((x) => (
              <option key={x}>{x}</option>
            ))}
          </select>
        </label>
        <label>
          State
          <select value={state} onChange={(e) => setState(e.target.value)}>
            <option value="all">All</option>
            {[
              "active",
              "resolved",
              "completed",
              "failed",
              "waiting",
              "unknown",
            ].map((x) => (
              <option key={x}>{x}</option>
            ))}
          </select>
        </label>
        <label>
          Evidence
          <select
            value={evidence}
            onChange={(e) => setEvidence(e.target.value)}
          >
            <option value="all">All</option>
            {["available", "partial", "stale", "missing", "unavailable"].map(
              (x) => (
                <option key={x}>{x}</option>
              ),
            )}
          </select>
        </label>
        <label>
          Seen state
          <select
            value={seenFilter}
            onChange={(e) => setSeenFilter(e.target.value)}
          >
            <option value="all">All</option>
            <option value="unseen">Unseen</option>
            <option value="seen">Seen</option>
          </select>
        </label>
      </div>
      {loading && <p role="status">Loading activity…</p>}
      {!loading && failed && (
        <DataStatusBanner state="partial">
          Activity is partial. Some activity sources are unavailable.
        </DataStatusBanner>
      )}
      {!loading && load.permissionLimited && (
        <DataStatusBanner state="partial">
          Some activity sources are not available with your current access.
        </DataStatusBanner>
      )}
      {!loading && !visible.length && (
        <p>
          {failed
            ? "No available source reported activity in this time range."
            : "No activity observed in this time range."}
        </p>
      )}
      {!!visible.length && (
        <>
          <button onClick={() => mark(visible.map((x) => x.key))}>
            Mark visible as seen
          </button>
          <ol
            className="activity-feed"
            aria-label="Recent operational activity"
          >
            {visible.map((item) => (
              <li
                key={item.key}
                className={seen.has(item.key) ? "seen" : "unseen"}
              >
                <button
                  className="activity-summary"
                  onClick={() => setSelected(item)}
                  aria-label={`Open details for ${item.title}`}
                >
                  <span>
                    <strong>{item.title}</strong>
                    <small>
                      {item.capabilityId} · {item.type.replaceAll("_", " ")}
                    </small>
                  </span>
                  <time dateTime={item.occurredAt}>
                    {new Date(item.occurredAt).toLocaleString()}
                  </time>
                </button>
                <div className="activity-meta">
                  <span>{item.severity ?? "No severity"}</span>
                  <span>{item.state}</span>
                  <span>{item.evidenceState} evidence</span>
                  <span>
                    {item.attention
                      ? `Needs attention: ${item.attention}`
                      : "Operational event"}
                  </span>
                  <span>{seen.has(item.key) ? "Seen" : "Unseen"}</span>
                </div>
                <div>
                  {activitySourcePath(item) && (
                    <Link to={activitySourcePath(item)!}>Open</Link>
                  )}{" "}
                  {activityInvestigationPath(item, timeRange) && (
                    <Link to={activityInvestigationPath(item, timeRange)!}>
                      Investigate
                    </Link>
                  )}{" "}
                  {!seen.has(item.key) && (
                    <button onClick={() => mark([item.key])}>
                      Mark as seen
                    </button>
                  )}
                </div>
              </li>
            ))}
          </ol>
        </>
      )}
      {selected && (
        <div
          className="activity-drawer-backdrop"
          onClick={() => setSelected(undefined)}
        >
          <aside
            className="activity-drawer"
            role="dialog"
            aria-modal="true"
            aria-labelledby="activity-detail-title"
            onClick={(e) => e.stopPropagation()}
          >
            <button ref={closeButton} onClick={() => setSelected(undefined)}>
              Close details
            </button>
            <h2 id="activity-detail-title">{selected.title}</h2>
            <dl>
              <dt>Activity type</dt>
              <dd>{selected.type.replaceAll("_", " ")}</dd>
              <dt>Occurred</dt>
              <dd>
                <time dateTime={selected.occurredAt}>
                  {new Date(selected.occurredAt).toLocaleString()}
                </time>
              </dd>
              <dt>Capability</dt>
              <dd>{selected.capabilityId}</dd>
              <dt>State</dt>
              <dd>{selected.state}</dd>
              <dt>Severity</dt>
              <dd>{selected.severity ?? "Not supplied"}</dd>
              <dt>Evidence</dt>
              <dd>{selected.evidenceState}</dd>
              <dt>Provenance</dt>
              <dd>{selected.provenance.replaceAll("_", " ")}</dd>
              <dt>Related entity</dt>
              <dd>{selected.entityType ?? "None"}</dd>
            </dl>
            {activitySourcePath(selected) && (
              <Link to={activitySourcePath(selected)!}>
                Open authoritative source
              </Link>
            )}{" "}
            {activityInvestigationPath(selected, timeRange) && (
              <Link to={activityInvestigationPath(selected, timeRange)!}>
                Investigate
              </Link>
            )}
          </aside>
        </div>
      )}
    </section>
  );
}
