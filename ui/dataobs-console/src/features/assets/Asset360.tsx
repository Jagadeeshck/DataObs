import { useEffect, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { api } from "../../api/client";
import { useProductContext } from "../../state/context";
const tabs = [
  "overview",
  "schema",
  "quality",
  "freshness",
  "lineage",
  "usage",
  "incidents",
  "changes",
  "slos",
  "cost",
  "related",
  "impact",
  "annotations",
];
const labels: Record<string, string[]> = {
  overview: [
    "name",
    "fqn",
    "asset_type",
    "health",
    "owner_team",
    "business_service",
    "source",
    "environment",
    "freshness",
    "quality",
    "active_incidents",
    "slo_state",
    "upstream_count",
    "downstream_count",
  ],
  schema: [
    "schema_fingerprint",
    "version",
    "columns",
    "constraints",
    "indexes",
    "partitions",
    "changes",
  ],
  quality: [
    "checks",
    "state",
    "recent_failures",
    "trend",
    "monitor_references",
  ],
  freshness: [
    "latest_source_timestamp",
    "observed_at",
    "age_seconds",
    "sla_seconds",
    "calculation_strategy",
    "breach_windows",
  ],
  lineage: [
    "nodes",
    "edges",
    "upstream",
    "downstream",
    "column_lineage",
    "truncated",
  ],
  usage: [
    "access_count",
    "unique_consumers",
    "top_consumers",
    "last_used",
    "trend",
    "coverage",
  ],
  incidents: ["incidents", "active_incidents"],
  changes: ["changes"],
  slos: ["slos", "items", "state"],
  cost: ["compute_cost", "storage_cost", "network_cost", "allocation_method"],
  related: ["related", "upstream", "downstream"],
  impact: ["affected", "affected_asset_ids", "active_incident_ids"],
  annotations: ["annotations", "items"],
};
function display(value: unknown): string {
  if (value === null || value === undefined || value === "") return "unknown";
  if (typeof value === "boolean") return value ? "yes" : "no";
  if (typeof value === "object")
    return Array.isArray(value) ? `${value.length} observed` : "available";
  return String(value);
}
export function Asset360() {
  const { assetId = "" } = useParams();
  const { tenant, environment } = useProductContext();
  const [params, setParams] = useSearchParams();
  const tab = tabs.includes(params.get("tab") ?? "")
    ? params.get("tab")!
    : "overview";
  const [data, setData] = useState<Record<string, unknown> | null>(null);
  const [status, setStatus] = useState("Loading…");
  useEffect(() => {
    const controller = new AbortController();
    const section = tab === "overview" ? "summary" : tab;
    api
      .assetSection(tenant, environment, assetId, section, controller.signal)
      .then((value) => {
        setData(value);
        setStatus("");
      })
      .catch(() => {
        setData(null);
        setStatus(`${tab} data is unknown or not configured`);
      });
    return () => controller.abort();
  }, [tenant, environment, assetId, tab]);
  return (
    <section className="page investigation-page">
      <div className="eyebrow">
        <Link to="/assets">ASSETS</Link> <span>/</span> ASSET 360
      </div>
      <div className="page-title">
        <div>
          <h1>{assetId}</h1>
          <p>
            Operational state, evidence, confidence and bounded impact for this
            entity.
          </p>
        </div>
        <div className="actions">
          <Link
            className="button-link"
            to={`/pathways?start=${encodeURIComponent(assetId)}`}
          >
            Open in Data Flow
          </Link>
          <button disabled title="Requires an allowlisted Kibana target">
            Open in Kibana
          </button>
        </div>
      </div>
      <nav className="tabs" aria-label="Asset investigation sections">
        {tabs.map((name) => (
          <button
            key={name}
            aria-current={tab === name ? "page" : undefined}
            onClick={() => setParams({ tab: name })}
          >
            {name}
          </button>
        ))}
      </nav>
      <section className="panel" aria-live="polite">
        <h2>{tab[0].toUpperCase() + tab.slice(1)}</h2>
        {status ? (
          <p className="notice">{status}</p>
        ) : (
          <>
            <p className="coverage-note">
              Data status: {String(data?.data_status ?? "unknown")} ·
              Confidence: {String(data?.confidence ?? "unknown")}
            </p>
            {data?.data_status === "not_configured" && (
              <p className="notice">
                This source is not configured. DataObs does not substitute a
                zero value.
              </p>
            )}
            <dl className="asset-facts">
              {labels[tab]
                .filter((key) => key in (data ?? {}))
                .map((key) => (
                  <div key={key}>
                    <dt>{key.replaceAll("_", " ")}</dt>
                    <dd>{display(data?.[key])}</dd>
                  </div>
                ))}
            </dl>
            {labels[tab].every((key) => !(key in (data ?? {}))) && (
              <p className="notice">
                No typed {tab} observations are available for this asset.
              </p>
            )}
            {labels[tab].flatMap((key) =>
              Array.isArray(data?.[key])
                ? (data?.[key] as Record<string, unknown>[]).map(
                    (item, index) => (
                      <article
                        className="evidence-card"
                        key={`${key}-${index}`}
                      >
                        <h3>
                          {display(
                            item.name ?? item.id ?? `${key} ${index + 1}`,
                          )}
                        </h3>
                        <dl>
                          {Object.entries(item)
                            .filter(([, value]) => typeof value !== "object")
                            .slice(0, 8)
                            .map(([name, value]) => (
                              <div key={name}>
                                <dt>{name.replaceAll("_", " ")}</dt>
                                <dd>{display(value)}</dd>
                              </div>
                            ))}
                        </dl>
                      </article>
                    ),
                  )
                : [],
            )}
          </>
        )}
      </section>
    </section>
  );
}
