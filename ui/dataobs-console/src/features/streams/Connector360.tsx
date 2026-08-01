import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import {
  streamsApi,
  type Detail,
  type List,
  type StreamConnector,
} from "../../api/streams";
import { useProductContext } from "../../state/context";
import {
  DataStatusBanner,
  EvidenceSummary,
  HealthBadge,
  MetricCard,
  MissingInputs,
  StaleIndicator,
  UnavailableState,
  display,
} from "./components";

const tabs = [
  "Overview",
  "Tasks",
  "Changes",
  "Incidents",
  "Monitors",
  "Evidence",
] as const;
const slug = (v: string) => v.toLowerCase();
export function Connector360() {
  const { connectorId = "" } = useParams(),
    { tenant, environment } = useProductContext();
  const [params, setParams] = useSearchParams(),
    active = Math.max(
      0,
      tabs.findIndex((v) => slug(v) === (params.get("tab") || "overview")),
    );
  const tab = tabs[active],
    refs = useRef<Array<HTMLButtonElement | null>>([]);
  const [overview, setOverview] = useState<Detail<StreamConnector>>(),
    [section, setSection] = useState<List<unknown>>(),
    [error, setError] = useState("");
  const load = useCallback(
    (signal?: AbortSignal) => {
      const common = [tenant, environment, connectorId] as const;
      const loaders = {
        Tasks: streamsApi.connectorTasks,
        Changes: streamsApi.connectorChanges,
        Incidents: streamsApi.connectorIncidents,
        Monitors: streamsApi.connectorMonitors,
      };
      const requests: Promise<unknown>[] = [
        streamsApi.connector(...common, signal).then(setOverview),
      ];
      if (tab in loaders)
        requests.push(
          loaders[tab as keyof typeof loaders](...common, signal).then((v) =>
            setSection(v as List<unknown>),
          ),
        );
      if (tab === "Evidence")
        requests.push(
          streamsApi
            .connectorEvidence(...common, signal)
            .then((v) => setSection(v as unknown as List<unknown>)),
        );
      Promise.all(requests)
        .then(() => setError(""))
        .catch((e: unknown) => {
          if (!signal?.aborted)
            setError(
              e instanceof Error
                ? e.message
                : "Unable to load connector evidence",
            );
        });
    },
    [tenant, environment, connectorId, tab],
  );
  useEffect(() => {
    const controller = new AbortController();
    load(controller.signal);
    return () => controller.abort();
  }, [load]);
  const select = (i: number) => {
    const next = new URLSearchParams(params);
    next.set("tab", slug(tabs[i]));
    setParams(next);
    requestAnimationFrame(() => refs.current[i]?.focus());
  };
  const item = overview?.item;
  return (
    <section className="page-card" aria-labelledby="connector-title">
      <nav aria-label="Breadcrumb">
        <Link to="/streams">Streams</Link> / Connectors
      </nav>
      <h1 id="connector-title">Connector 360</h1>
      <p className="wrap-anywhere">
        <strong>{item?.name ?? connectorId}</strong>
      </p>
      <button type="button" onClick={() => load()}>
        Refresh evidence
      </button>
      {error ? (
        <UnavailableState message={error} />
      ) : overview ? (
        <DataStatusBanner
          status={overview.data_status}
          warnings={overview.warnings}
          observedAt={overview.observed_at}
        />
      ) : (
        <p role="status">Loading measured evidence…</p>
      )}
      <div
        role="tablist"
        aria-label="Connector details"
        className="tabs"
        onKeyDown={(e) => {
          if (!["ArrowLeft", "ArrowRight"].includes(e.key)) return;
          e.preventDefault();
          select(
            (active + (e.key === "ArrowRight" ? 1 : -1) + tabs.length) %
              tabs.length,
          );
        }}
      >
        {tabs.map((name, i) => (
          <button
            key={name}
            ref={(n) => {
              refs.current[i] = n;
            }}
            role="tab"
            aria-selected={i === active}
            tabIndex={i === active ? 0 : -1}
            aria-controls={`connector-panel-${slug(name)}`}
            id={`connector-tab-${slug(name)}`}
            onClick={() => select(i)}
          >
            {name}
          </button>
        ))}
      </div>
      <section
        role="tabpanel"
        tabIndex={0}
        id={`connector-panel-${slug(tab)}`}
        aria-labelledby={`connector-tab-${slug(tab)}`}
      >
        <h2>{tab}</h2>
        {tab === "Overview" && item && (
          <>
            <div className="metric-grid">
              <MetricCard label="Type" value={item.connector_type} />
              <MetricCard label="Classification" value={item.classification} />
              <MetricCard label="State" value={item.state} />
              <MetricCard label="Tasks" value={item.task_count} />
              <MetricCard label="Failed tasks" value={item.failed_task_count} />
              <MetricCard label="Workers" value={item.worker_count} />
              <MetricCard
                label="Configuration fingerprint"
                value={item.config_fingerprint}
              />
              <MetricCard
                label="Class fingerprint"
                value={item.class_fingerprint}
              />
            </div>
            <HealthBadge health={item.health} />
            {overview.data_status === "stale" && <StaleIndicator />}
            <p>Reason codes: {item.reason_codes?.join(", ") || "Unknown"}</p>
            <EvidenceSummary
              coverage={overview.source_coverage}
              confidence={overview.confidence}
            />
            <MissingInputs inputs={overview.missing_inputs} />
            {item.cluster_id && (
              <p>
                <Link
                  to={`/streams/clusters/${encodeURIComponent(item.cluster_id)}`}
                >
                  Open cluster
                </Link>
              </p>
            )}
          </>
        )}
        {tab === "Changes" && section?.data_status === "not_configured" ? (
          <p role="status">Change detection is not configured</p>
        ) : tab === "Evidence" ? (
          <EvidenceSummary
            coverage={overview?.source_coverage}
            confidence={overview?.confidence}
          />
        ) : (
          tab !== "Overview" && (
            <EvidenceTable
              title={`Connector ${tab}`}
              rows={section?.items ?? []}
            />
          )
        )}
      </section>
    </section>
  );
}
function EvidenceTable({ title, rows }: { title: string; rows: unknown[] }) {
  const objects = rows.filter(
    (r): r is Record<string, unknown> => !!r && typeof r === "object",
  );
  const keys = Array.from(new Set(objects.flatMap(Object.keys)))
    .filter((k) => !["evidence_refs", "reason_codes"].includes(k))
    .slice(0, 8);
  if (!objects.length)
    return <p>No measured evidence is available for this view.</p>;
  return (
    <div className="table-scroll" tabIndex={0}>
      <table>
        <caption>{title}</caption>
        <thead>
          <tr>
            {keys.map((k) => (
              <th key={k} scope="col">
                {k.replaceAll("_", " ")}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {objects.map((row, i) => (
            <tr
              key={String(row.task_id ?? row.change_id ?? row.incident_id ?? i)}
            >
              {keys.map((k) => (
                <td key={k} className="wrap-anywhere">
                  {display(
                    typeof row[k] === "object"
                      ? JSON.stringify(row[k])
                      : (row[k] as string | number | null),
                  )}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
