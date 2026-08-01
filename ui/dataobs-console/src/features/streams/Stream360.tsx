import { useEffect, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { api, type StreamResponse } from "../../api/client";
import { useProductContext } from "../../state/context";
import type { LagCell, MetricSample, Partition } from "../../api/client";
import {
  AccessibleSparkline,
  HealthBadge,
  LagHeatmap,
  MissingInputs,
  PartitionHealthGrid,
  display,
} from "./components";

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
    "Throughput",
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
    "Offsets",
    "Retention Risk",
    "Rebalances",
    "Applications",
    "Incidents",
    "RCA",
    "Monitors",
    "Changes",
  ],
} as const;
const roots = {
  cluster: "stream-clusters",
  topic: "streams",
  group: "consumer-groups",
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
  const object =
    data && typeof data === "object" && !Array.isArray(data)
      ? (data as { [key: string]: unknown })
      : undefined;
  const allowed =
    kind === "topic"
      ? [
          "topic",
          "name",
          "cluster_id",
          "health",
          "reason_codes",
          "partition_count",
          "replication_factor",
          "cleanup_policy",
          "retention_ms",
          "min_insync_replicas",
          "producer_rate",
          "consumer_rate",
          "maximum_lag",
          "retention_risk",
          "schema_state",
          "connector_state",
          "observed_at",
          "source_coverage",
        ]
      : [
          "group_id",
          "cluster_id",
          "state",
          "protocol",
          "coordinator",
          "member_count",
          "assigned_partition_count",
          "total_lag",
          "maximum_lag",
          "lag_velocity",
          "drain_time",
          "retention_risk",
          "rebalance_count",
          "observed_at",
          "source_coverage",
        ];
  const rows = Array.isArray(data)
    ? (data as Array<{ [key: string]: unknown }>)
    : [];
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
            {kind === "topic" && selected === "partitions" ? (
              <PartitionHealthGrid
                partitions={rows as unknown as Partition[]}
              />
            ) : null}
            {kind === "topic" && selected === "throughput" ? (
              <div className="chart-grid">
                {[
                  "records_per_second",
                  "bytes_per_second",
                  "producer_rate",
                  "consumer_rate",
                ].map((key) => (
                  <AccessibleSparkline
                    key={key}
                    label={key.replaceAll("_", " ")}
                    unit={key === "bytes_per_second" ? "bytes/s" : "records/s"}
                    samples={object?.[key] as MetricSample[] | undefined}
                  />
                ))}
              </div>
            ) : null}
            {kind === "group" &&
            (selected === "lag" || selected === "lag-heatmap") ? (
              <LagHeatmap
                cells={
                  (Array.isArray(data)
                    ? data
                    : (object?.by_partition ?? [])) as LagCell[]
                }
              />
            ) : null}
            <dl className="stream-facts">
              {object ? (
                allowed
                  .filter((key) => key in object)
                  .map((key) => [key, object[key]] as [string, unknown])
                  .map(([key, value]) => (
                    <div key={key}>
                      <dt>{key.replaceAll("_", " ")}</dt>
                      <dd>
                        {Array.isArray(value)
                          ? value.map(String).join(", ") || "Unknown"
                          : typeof value === "object"
                            ? "Measured details available below"
                            : display(
                                value as string | number | null | undefined,
                              )}
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
            <MissingInputs inputs={response.missing_inputs} />
            {kind === "topic" && selected === "overview" && (
              <aside className="explanation">
                <h3>Health explanation</h3>
                <HealthBadge health={String(object?.health ?? "unknown")} />
                <p>
                  {Array.isArray(object?.reason_codes)
                    ? object.reason_codes.join("; ")
                    : "No measured reason codes are available."}
                </p>
              </aside>
            )}
            {kind === "group" &&
              selected === "retention-risk" &&
              object?.compacted_only === true && (
                <p>
                  Compacted-only topics are not evaluated with delete-retention
                  calculations.
                </p>
              )}
          </>
        )}
      </section>
    </section>
  );
}
