import { useEffect, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { api, type StreamResponse } from "../../api/client";
import { useProductContext } from "../../state/context";

const tabs = {
  cluster: [
    "Overview",
    "Brokers",
    "Topics",
    "Consumer Groups",
    "Connectors",
    "Health",
    "Changes",
    "Incidents",
    "Cost",
  ],
  topic: [
    "Overview",
    "Data Flow",
    "Partitions",
    "Consumer Groups",
    "Producers",
    "Consumers",
    "Connectors",
    "Schemas",
    "Configuration",
    "Incidents",
    "Monitors",
    "Changes",
    "Cost",
  ],
  group: [
    "Overview",
    "Lag",
    "Members",
    "Assignments",
    "Rebalances",
    "Applications",
    "Incidents",
    "RCA",
    "Monitors",
    "Changes",
  ],
  connector: ["Overview", "Tasks", "Changes", "Incidents", "RCA", "Actions"],
  schema: [
    "Overview",
    "Versions",
    "Changes",
    "Impact",
    "Incidents",
    "Monitors",
  ],
} as const;
const roots = {
  cluster: "stream-clusters",
  topic: "streams",
  group: "consumer-groups",
  connector: "stream-connectors",
  schema: "schema-subjects",
};
const slug = (value: string) =>
  value.toLowerCase().replaceAll(" ", "-").replace("data-flow", "pathways");

export function Stream360({ kind }: { kind: keyof typeof tabs }) {
  const { tenant, environment } = useProductContext();
  const route = useParams();
  const id = Object.values(route)[0] ?? "unknown";
  const [params, setParams] = useSearchParams();
  const selected = params.get("tab") ?? "overview";
  const activeIndex = Math.max(
    0,
    tabs[kind].findIndex((tab) => slug(tab) === selected),
  );
  const [response, setResponse] = useState<StreamResponse>();
  const [error, setError] = useState("");
  useEffect(() => {
    const controller = new AbortController();
    const section =
      activeIndex === 0 ? undefined : slug(tabs[kind][activeIndex]);
    api
      .streamSection(
        tenant,
        environment,
        roots[kind],
        id,
        section,
        controller.signal,
      )
      .then(setResponse)
      .catch((cause: unknown) => {
        if (!controller.signal.aborted)
          setError(
            cause instanceof Error ? cause.message : "Unable to load evidence",
          );
      });
    return () => controller.abort();
  }, [tenant, environment, kind, id, activeIndex]);
  const data = response?.item ?? response?.data;
  return (
    <section aria-labelledby="stream-title" className="page-card">
      <nav aria-label="Breadcrumb">
        <Link to="/streams">Streams</Link> / {kind}
      </nav>
      <h1 id="stream-title">
        {kind === "group"
          ? "Consumer Group"
          : `${kind[0].toUpperCase()}${kind.slice(1)}`}{" "}
        360
      </h1>
      <p>
        <strong>{id}</strong>
      </p>
      <div role="status" aria-live="polite" className="data-state">
        {response
          ? `${response.data_status} — observed ${new Date(response.observed_at).toLocaleString()}`
          : error
            ? `Unavailable — ${error}`
            : "Loading measured evidence…"}
      </div>
      <div
        role="tablist"
        aria-label={`${kind} details`}
        className="tabs"
        onKeyDown={(event) => {
          if (!["ArrowLeft", "ArrowRight"].includes(event.key)) return;
          const delta = event.key === "ArrowRight" ? 1 : -1;
          const next =
            (activeIndex + delta + tabs[kind].length) % tabs[kind].length;
          setParams({ tab: slug(tabs[kind][next]) });
        }}
      >
        {tabs[kind].map((tab, index) => (
          <button
            key={tab}
            id={`tab-${slug(tab)}`}
            role="tab"
            aria-selected={index === activeIndex}
            aria-controls={`panel-${slug(tab)}`}
            tabIndex={index === activeIndex ? 0 : -1}
            onClick={() => setParams({ tab: slug(tab) })}
          >
            {tab}
          </button>
        ))}
      </div>
      <section
        role="tabpanel"
        id={`panel-${slug(tabs[kind][activeIndex])}`}
        aria-labelledby={`tab-${slug(tabs[kind][activeIndex])}`}
        tabIndex={0}
      >
        <h2>{tabs[kind][activeIndex]}</h2>
        {response && (
          <>
            <dl className="stream-facts">
              {data && typeof data === "object" ? (
                Object.entries(data)
                  .slice(0, 40)
                  .map(([key, value]) => (
                    <div key={key}>
                      <dt>{key.replaceAll("_", " ")}</dt>
                      <dd>
                        {value === null || value === undefined
                          ? "Unknown"
                          : typeof value === "object"
                            ? JSON.stringify(value)
                            : String(value)}
                      </dd>
                    </div>
                  ))
              ) : (
                <div>
                  <dt>Status</dt>
                  <dd>Not configured</dd>
                </div>
              )}
            </dl>
            {response.missing_inputs.length > 0 && (
              <p>Missing inputs: {response.missing_inputs.join(", ")}</p>
            )}
          </>
        )}
      </section>
    </section>
  );
}
