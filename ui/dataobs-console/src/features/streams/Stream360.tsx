import { Link, useParams } from "react-router-dom";

const tabs: Record<string, string[]> = {
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
};

export function Stream360({ kind }: { kind: keyof typeof tabs }) {
  const params = useParams();
  const id = Object.values(params)[0] ?? "unknown";
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
      <div role="status" className="data-state">
        ◌ Partial data — source coverage and confidence are preserved; missing
        telemetry is not shown as healthy.
      </div>
      <div role="tablist" aria-label={`${kind} details`} className="tabs">
        {tabs[kind].map((tab, index) => (
          <button key={tab} role="tab" aria-selected={index === 0}>
            {tab}
          </button>
        ))}
      </div>
      <section aria-labelledby="evidence-title">
        <h2 id="evidence-title">Operational evidence</h2>
        <p>
          Measured Kafka evidence will appear here when the tenant-scoped
          observer projection is available.
        </p>
      </section>
    </section>
  );
}
