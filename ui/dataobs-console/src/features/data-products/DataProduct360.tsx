import { useEffect, useState } from "react";
import { useParams, useSearchParams } from "react-router-dom";
import { api, type DataProduct } from "../../api/client";
import { useProductContext } from "../../state/context";
const tabs = [
  "Overview",
  "Outputs",
  "Members",
  "Lineage",
  "Dependencies",
  "SLOs",
  "Reliability",
  "Incidents",
  "Changes",
  "Impact",
  "Revisions",
];
export function DataProduct360() {
  const { productId = "" } = useParams();
  const { tenant, environment } = useProductContext();
  const [params, setParams] = useSearchParams();
  const active = params.get("tab") ?? "Overview";
  const [product, setProduct] = useState<DataProduct>();
  const [error, setError] = useState<string>();
  useEffect(() => {
    const controller = new AbortController();
    api
      .dataProduct(tenant, environment, productId, controller.signal)
      .then((x) => setProduct(x.product))
      .catch(() =>
        setError(
          "This Data Product was not found or is not available in the trusted scope.",
        ),
      );
    return () => controller.abort();
  }, [tenant, environment, productId]);
  if (error)
    return (
      <section>
        <h1>Data Product unavailable</h1>
        <p role="alert">{error}</p>
      </section>
    );
  if (!product) return <p role="status">Loading Product 360…</p>;
  return (
    <article>
      <header>
        <h1>{product.name}</h1>
        <p>{product.description || "No description configured."}</p>
        <p>
          <strong>{product.lifecycle_state}</strong> · {product.criticality} ·
          Owned by {product.owner.team}
        </p>
      </header>
      <div className="tabs" role="tablist" aria-label="Product 360 sections">
        {tabs.map((tab) => (
          <button
            key={tab}
            role="tab"
            aria-selected={active === tab}
            onClick={() => setParams({ tab })}
          >
            {tab}
          </button>
        ))}
      </div>
      <section role="tabpanel" aria-labelledby={`tab-${active}`}>
        <h2 id={`tab-${active}`}>{active}</h2>
        {active === "Overview" && (
          <dl className="asset-facts">
            <div>
              <dt>Domain</dt>
              <dd>{product.domain}</dd>
            </div>
            <div>
              <dt>Reliability</dt>
              <dd>Unknown — no current evidence</dd>
            </div>
            <div>
              <dt>Coverage</dt>
              <dd>Unknown — no current evidence</dd>
            </div>
            <div>
              <dt>Revision</dt>
              <dd>{product.revision}</dd>
            </div>
          </dl>
        )}
        {active === "Outputs" &&
          (product.outputs.length ? (
            <ul>
              {product.outputs.map((x) => (
                <li key={`${x.entity_type}:${x.entity_id}`}>
                  {x.display_name || x.entity_id} ({x.entity_type})
                  {x.primary ? " — primary" : ""}
                </li>
              ))}
            </ul>
          ) : (
            <p>No outputs configured.</p>
          ))}
        {active !== "Overview" && active !== "Outputs" && (
          <div role="status">
            <p>
              This section is not configured or its evidence is unavailable.
            </p>
            <p>Unknown is never treated as healthy.</p>
          </div>
        )}
      </section>
    </article>
  );
}
