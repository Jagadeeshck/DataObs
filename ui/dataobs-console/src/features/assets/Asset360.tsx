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
];
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
            <pre className="evidence-view">{JSON.stringify(data, null, 2)}</pre>
          </>
        )}
      </section>
    </section>
  );
}
