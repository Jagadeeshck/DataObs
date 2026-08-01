import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import {
  api,
  type ClusterChange,
  type ClusterConnectorSummary,
  type ClusterConsumerGroupSummary,
  type ClusterHealthSummary,
  type ClusterListResponse,
  type ClusterTopicSummary,
  type EvidenceEnvelope,
  type IncidentSummary,
  type KafkaBroker,
  type KafkaCluster,
  type SectionResponse,
} from "../../api/client";
import { useProductContext } from "../../state/context";
import {
  DataStatusBanner,
  EmptyState,
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
  "Brokers",
  "Topics",
  "Consumer Groups",
  "Connectors",
  "Health",
  "Changes",
  "Incidents",
] as const;
const slug = (value: string) => value.toLowerCase().replaceAll(" ", "-");
type Tab = (typeof tabs)[number];
type List = ClusterListResponse<
  | KafkaBroker
  | ClusterTopicSummary
  | ClusterConsumerGroupSummary
  | ClusterConnectorSummary
  | ClusterChange
  | IncidentSummary
>;

export function Cluster360() {
  const { clusterId = "" } = useParams();
  const { tenant, environment } = useProductContext();
  const [params, setParams] = useSearchParams();
  const active = Math.max(
    0,
    tabs.findIndex((tab) => slug(tab) === (params.get("tab") ?? "overview")),
  );
  const tab = tabs[active];
  const [cluster, setCluster] = useState<SectionResponse<KafkaCluster>>();
  const [health, setHealth] = useState<
    ClusterHealthSummary & EvidenceEnvelope
  >();
  const [list, setList] = useState<List>();
  const [error, setError] = useState("");
  const [polling, setPolling] = useState(false);
  const tabRefs = useRef<Array<HTMLButtonElement | null>>([]);

  const load = useCallback(
    (signal?: AbortSignal) => {
      const common = [tenant, environment, clusterId] as const;
      const query = new URLSearchParams(params);
      query.delete("tab");
      const requests: Promise<unknown>[] = [
        api.cluster(...common, signal).then(setCluster),
      ];
      if (tab === "Overview" || tab === "Health")
        requests.push(api.clusterHealth(...common, signal).then(setHealth));
      else {
        const loaders: Partial<Record<Tab, Promise<List>>> = {
          Brokers: api.clusterBrokers(
            ...common,
            query,
            signal,
          ) as Promise<List>,
          Topics: api.clusterTopics(...common, query, signal) as Promise<List>,
          "Consumer Groups": api.clusterConsumerGroups(
            ...common,
            query,
            signal,
          ) as Promise<List>,
          Connectors: api.clusterConnectors(
            ...common,
            query,
            signal,
          ) as Promise<List>,
          Changes: api.clusterChanges(
            ...common,
            query,
            signal,
          ) as Promise<List>,
          Incidents: api.clusterIncidents(
            ...common,
            query,
            signal,
          ) as Promise<List>,
        };
        const request = loaders[tab];
        if (request) requests.push(request.then(setList));
      }
      Promise.all(requests)
        .then(() => setError(""))
        .catch((cause: unknown) => {
          if (!signal?.aborted)
            setError(
              cause instanceof Error
                ? cause.message
                : "Unable to load cluster evidence",
            );
        });
    },
    [tenant, environment, clusterId, tab, params],
  );

  useEffect(() => {
    const controller = new AbortController();
    load(controller.signal);
    return () => controller.abort();
  }, [load]);
  useEffect(() => {
    if (!polling) return;
    const timer = window.setInterval(() => {
      if (document.visibilityState === "visible") load();
    }, 30_000);
    return () => window.clearInterval(timer);
  }, [polling, load]);

  const selectTab = (index: number) => {
    const next = new URLSearchParams();
    next.set("tab", slug(tabs[index]));
    setParams(next);
    requestAnimationFrame(() => tabRefs.current[index]?.focus());
  };
  const envelope =
    tab === "Overview" ? cluster : tab === "Health" ? health : list;
  return (
    <section aria-labelledby="cluster-title" className="page-card cluster-360">
      <nav aria-label="Breadcrumb">
        <Link to="/streams">Streams</Link> / Clusters
      </nav>
      <div className="cluster-heading">
        <div>
          <h1 id="cluster-title">Kafka Cluster 360</h1>
          <p className="wrap-anywhere">
            <strong>{cluster?.item?.name ?? clusterId}</strong> · {clusterId}
          </p>
        </div>
        <div>
          <button type="button" onClick={() => load()}>
            Refresh evidence
          </button>{" "}
          <label>
            <input
              type="checkbox"
              checked={polling}
              onChange={(event) => setPolling(event.target.checked)}
            />{" "}
            Poll every 30 seconds
          </label>
        </div>
      </div>
      {error ? (
        <UnavailableState message={error} />
      ) : envelope ? (
        <DataStatusBanner
          status={envelope.data_status}
          warnings={envelope.warnings}
          observedAt={envelope.observed_at}
        />
      ) : (
        <p role="status">Loading measured evidence…</p>
      )}
      <div
        role="tablist"
        aria-label="Cluster details"
        className="tabs"
        onKeyDown={(event) => {
          if (!["ArrowLeft", "ArrowRight"].includes(event.key)) return;
          event.preventDefault();
          selectTab(
            (active + (event.key === "ArrowRight" ? 1 : -1) + tabs.length) %
              tabs.length,
          );
        }}
      >
        {tabs.map((name, index) => (
          <button
            ref={(node) => {
              tabRefs.current[index] = node;
            }}
            key={name}
            role="tab"
            id={`cluster-tab-${slug(name)}`}
            aria-selected={index === active}
            aria-controls={`cluster-panel-${slug(name)}`}
            tabIndex={index === active ? 0 : -1}
            onClick={() => selectTab(index)}
          >
            {name}
          </button>
        ))}
      </div>
      <section
        role="tabpanel"
        tabIndex={0}
        id={`cluster-panel-${slug(tab)}`}
        aria-labelledby={`cluster-tab-${slug(tab)}`}
      >
        <h2>{tab}</h2>
        {tab === "Overview" && (
          <Overview cluster={cluster?.item} health={health} />
        )}
        {tab === "Health" && <HealthView health={health} />}
        {tab === "Topics" && (
          <TopicFilters params={params} setParams={setParams} />
        )}
        {!error && !["Overview", "Health"].includes(tab) && (
          <ResourceTable
            tab={tab}
            response={list}
            onNext={(cursor) => {
              const next = new URLSearchParams(params);
              next.set("cursor", cursor);
              setParams(next);
            }}
          />
        )}
      </section>
    </section>
  );
}

function Overview({
  cluster,
  health,
}: {
  cluster?: KafkaCluster;
  health?: ClusterHealthSummary & EvidenceEnvelope;
}) {
  if (!cluster || !health) return <p role="status">Loading overview…</p>;
  return (
    <>
      <div className="metric-grid">
        <MetricCard label="Health" value={health.health} />
        <MetricCard label="Controller" value={cluster.controller_id} />
        <MetricCard label="Brokers" value={health.broker_count} />
        <MetricCard label="Topics" value={health.topic_count} />
        <MetricCard label="Partitions" value={health.partition_count} />
        <MetricCard
          label="Consumer groups"
          value={health.consumer_group_count}
        />
        <MetricCard label="Connectors" value={health.connector_count} />
        <MetricCard
          label="Under-replicated partitions"
          value={health.under_replicated_partition_count}
        />
        <MetricCard
          label="Leaderless partitions"
          value={health.leaderless_partition_count}
        />
        <MetricCard
          label="Offline replicas"
          value={health.offline_replica_count}
        />
        <MetricCard
          label="Failed connectors"
          value={health.failed_connector_count}
        />
      </div>
      <h3>Health explanation</h3>
      <p>
        <HealthBadge health={health.health} /> Evidence codes:{" "}
        {health.reason_codes.join(", ") || "No explanation available"}.
      </p>
      <EvidenceSummary
        coverage={health.source_coverage}
        confidence={health.confidence}
      />
      <MissingInputs inputs={health.missing_inputs} />
      {health.data_status === "stale" || health.stale_resource_count ? (
        <p>
          <StaleIndicator /> Some observations exceed the freshness window.
        </p>
      ) : null}
    </>
  );
}

function HealthView({
  health,
}: {
  health?: ClusterHealthSummary & EvidenceEnvelope;
}) {
  if (!health) return <p role="status">Loading health evidence…</p>;
  const rows = [
    ["Healthy brokers", health.healthy_brokers],
    ["Unhealthy brokers", health.unhealthy_brokers],
    ["Degraded topics", health.degraded_topic_count],
    ["Critical topics", health.critical_topic_count],
    ["Under-replicated partitions", health.under_replicated_partition_count],
    ["Leaderless partitions", health.leaderless_partition_count],
    ["Failed connectors", health.failed_connector_count],
    ["Stale resources", health.stale_resource_count],
  ] as const;
  return (
    <>
      <p className="sr-only">
        Operational resource health distribution. Values are measured resource
        counts; unknown means evidence is missing.
      </p>
      <p>
        Cluster health is <strong>{health.health}</strong>. Counts below are
        resources, partitions, replicas, or connectors as labelled and do not
        claim root cause.
      </p>
      <div className="responsive-table">
        <table>
          <caption>
            Text and table alternative for cluster health summary
          </caption>
          <thead>
            <tr>
              <th scope="col">Measure</th>
              <th scope="col">Measured count</th>
            </tr>
          </thead>
          <tbody>
            {rows.map(([label, value]) => (
              <tr key={label}>
                <th scope="row">{label}</th>
                <td>{display(value)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <h3>Priority issues</h3>
      <ul>
        {health.reason_codes.map((reason) => (
          <li key={reason}>{reason.replaceAll("_", " ")}</li>
        ))}
      </ul>
      <MissingInputs inputs={health.missing_inputs} />
    </>
  );
}

function TopicFilters({
  params,
  setParams,
}: {
  params: URLSearchParams;
  setParams: (next: URLSearchParams) => void;
}) {
  const update = (key: string, value: string) => {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value);
    else next.delete(key);
    next.delete("cursor");
    setParams(next);
  };
  return (
    <div className="filter-row" aria-label="Topic filters">
      <label>
        Search{" "}
        <input
          value={params.get("search") ?? ""}
          onChange={(e) => update("search", e.target.value)}
        />
      </label>
      <label>
        Health{" "}
        <select
          value={params.get("health") ?? ""}
          onChange={(e) => update("health", e.target.value)}
        >
          <option value="">All</option>
          <option>healthy</option>
          <option>degraded</option>
          <option>critical</option>
        </select>
      </label>
      <label>
        Retention risk{" "}
        <select
          value={params.get("retention_risk") ?? ""}
          onChange={(e) => update("retention_risk", e.target.value)}
        >
          <option value="">All</option>
          <option>at_risk</option>
          <option>safe</option>
        </select>
      </label>
      <label>
        Lag{" "}
        <select
          value={params.get("has_lag") ?? ""}
          onChange={(e) => update("has_lag", e.target.value)}
        >
          <option value="">Any</option>
          <option value="true">Has lag</option>
          <option value="false">Zero measured lag</option>
        </select>
      </label>
      <label>
        Sort{" "}
        <select
          value={params.get("sort") ?? "topic"}
          onChange={(e) => update("sort", e.target.value)}
        >
          <option value="topic">Topic</option>
          <option value="health">Health</option>
          <option value="maximum_lag">Maximum lag</option>
          <option value="last_observed">Last observed</option>
        </select>
      </label>
    </div>
  );
}

function ResourceTable({
  tab,
  response,
  onNext,
}: {
  tab: Tab;
  response?: List;
  onNext: (cursor: string) => void;
}) {
  if (!response) return <p role="status">Loading {tab.toLowerCase()}…</p>;
  if (response.data_status === "not_configured")
    return (
      <EmptyState>
        Not configured. An empty result is not evidence that no{" "}
        {tab.toLowerCase()} occurred.
      </EmptyState>
    );
  if (!response.items.length) return <EmptyState />;
  const columns: Record<string, string[]> = {
    Brokers: [
      "broker_id",
      "host",
      "port",
      "rack",
      "controller",
      "health",
      "reason_codes",
      "observed_at",
    ],
    Topics: [
      "topic",
      "health",
      "partition_count",
      "replication_factor",
      "maximum_lag",
      "producer_rate",
      "consumer_rate",
      "retention_risk",
      "consumer_group_count",
      "observed_at",
    ],
    "Consumer Groups": [
      "group_id",
      "state",
      "protocol",
      "member_count",
      "assigned_partition_count",
      "total_lag",
      "maximum_lag",
      "lag_velocity",
      "drain_time",
      "retention_risk",
      "observed_at",
    ],
    Connectors: [
      "connector_id",
      "connector_type",
      "state",
      "task_count",
      "failed_task_count",
      "worker_count",
      "classification",
      "observed_at",
      "data_status",
    ],
    Changes: [
      "observed_at",
      "resource_type",
      "resource_id",
      "change_type",
      "previous_fingerprint",
      "new_fingerprint",
      "source",
      "confidence",
    ],
    Incidents: [
      "incident_id",
      "title",
      "severity",
      "state",
      "affected_resource",
      "opened_at",
      "observed_at",
      "relationship",
    ],
  };
  const keys = columns[tab] ?? [];
  const brokerItems =
    tab === "Brokers" ? (response.items as KafkaBroker[]) : [];
  return (
    <>
      {tab === "Brokers" ? (
        <div className="metric-grid" aria-label="Broker summary">
          <MetricCard label="Total brokers" value={brokerItems.length} />
          <MetricCard
            label="Healthy brokers"
            value={
              brokerItems.filter((item) => item.health === "healthy").length
            }
          />
          <MetricCard
            label="Unhealthy brokers"
            value={
              brokerItems.filter(
                (item) =>
                  item.health &&
                  item.health !== "healthy" &&
                  item.health !== "unknown",
              ).length
            }
          />
          <MetricCard
            label="Controller broker"
            value={brokerItems.find((item) => item.controller)?.broker_id}
          />
          <MetricCard
            label="Unknown status"
            value={
              brokerItems.filter(
                (item) => !item.health || item.health === "unknown",
              ).length
            }
          />
        </div>
      ) : null}
      <EvidenceSummary
        coverage={response.source_coverage}
        confidence={response.confidence}
      />
      <MissingInputs inputs={response.missing_inputs} />
      <div className="responsive-table">
        <table>
          <caption>
            {tab} measured for this cluster; unknown values were not observed.
          </caption>
          <thead>
            <tr>
              {keys.map((key) => (
                <th scope="col" key={key}>
                  {key.replaceAll("_", " ")}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {response.items.map((raw, index) => {
              const item = raw as unknown as Record<string, unknown>;
              return (
                <tr
                  key={String(
                    item.broker_id ??
                      item.topic ??
                      item.group_id ??
                      item.connector_id ??
                      item.incident_id ??
                      index,
                  )}
                >
                  {keys.map((key) => (
                    <td className="wrap-anywhere" key={key}>
                      {linkedValue(tab, key, item)}
                    </td>
                  ))}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      {response.next_cursor && (
        <button type="button" onClick={() => onNext(response.next_cursor!)}>
          Next page
        </button>
      )}
    </>
  );
}

function linkedValue(tab: Tab, key: string, item: Record<string, unknown>) {
  const value = item[key];
  if (tab === "Brokers" && key === "controller")
    return value === true
      ? "Controller broker"
      : value === false
        ? "Not controller"
        : "Unknown";
  if (key === "reason_codes" && Array.isArray(value))
    return value.join(", ") || "None measured";
  if (tab === "Topics" && key === "topic")
    return (
      <Link
        to={`/streams/topics/${encodeURIComponent(String(item.stream_id ?? value))}`}
      >
        {display(value as string)}
      </Link>
    );
  if (tab === "Consumer Groups" && key === "group_id")
    return (
      <Link
        to={`/streams/consumer-groups/${encodeURIComponent(String(value))}`}
      >
        {display(value as string)}
      </Link>
    );
  if (tab === "Connectors" && key === "connector_id")
    return (
      <Link to={`/streams/connectors/${encodeURIComponent(String(value))}`}>
        {display(value as string)}
      </Link>
    );
  if (tab === "Incidents" && key === "incident_id")
    return (
      <Link to={`/incidents/${encodeURIComponent(String(value))}`}>
        {display(value as string)}
      </Link>
    );
  if ((key === "total_lag" || key === "maximum_lag") && value === 0)
    return "0 (measured zero lag)";
  return display(value as string | number | null | undefined);
}
