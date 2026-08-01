import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { accessToken } from "../../auth/oidc";
import { instrumentedFetch } from "../../observability";
import {
  DataStatusBanner,
  HealthBadge,
  LoadingSkeleton,
} from "../../components/Evidence";
import { useProductContext } from "../../state/context";

export type IntegrationSupport =
  | "supported"
  | "preview"
  | "planned"
  | "not_available";
export interface IntegrationMetadata {
  id: string;
  name: string;
  category: string;
  support_status: IntegrationSupport;
  configuration_state: "configured" | "not_configured" | "unavailable";
  connection_state?: "connected" | "degraded" | "failed" | "unknown";
  last_successful_collection?: string;
  last_failure?: string;
  coverage?: number;
  required_permissions?: string[];
  documentation_url?: string;
  purpose?: string;
  data_collected?: string[];
  data_not_collected?: string[];
  network_access?: string[];
  secret_handling?: string;
  collection_frequency?: string;
  setup_instructions?: string[];
}

async function loadCatalog(
  tenant: string,
  environment: string,
  signal: AbortSignal,
): Promise<IntegrationMetadata[]> {
  const token = await accessToken();
  const response = await instrumentedFetch(
    `/api/v1/integrations/metadata?environment=${encodeURIComponent(environment)}`,
    {
      signal,
      credentials: "include",
      headers: {
        "X-DataObs-Tenant": tenant,
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
    },
  );
  if (response.status === 404 || response.status === 501)
    throw Object.assign(
      new Error("The Team 4 integration metadata contract is unavailable."),
      { expected: true },
    );
  if (!response.ok)
    throw new Error("Integration metadata could not be loaded.");
  const body = (await response.json()) as { items?: IntegrationMetadata[] };
  return body.items ?? [];
}
function useIntegrations() {
  const { tenant, environment, refreshGeneration } = useProductContext();
  const [items, setItems] = useState<IntegrationMetadata[]>();
  const [error, setError] = useState<Error>();
  useEffect(() => {
    if (!tenant || !environment) return;
    const controller = new AbortController();
    // eslint-disable-next-line react-hooks/set-state-in-effect -- reset belongs to this external request generation
    setError(undefined);
    void loadCatalog(tenant, environment, controller.signal)
      .then(setItems)
      .catch((reason: Error) => {
        if (reason.name !== "AbortError") setError(reason);
      });
    return () => controller.abort();
  }, [tenant, environment, refreshGeneration]);
  return { items, error };
}
export function Integrations() {
  const { items, error } = useIntegrations();
  if (!items && !error)
    return (
      <div className="page">
        <LoadingSkeleton label="Loading supported integration metadata…" />
      </div>
    );
  return (
    <div className="page">
      <div className="page-title">
        <div>
          <div className="eyebrow">CONFIGURE / INTEGRATIONS</div>
          <h1>Integrations</h1>
          <p>
            Support and collection state are reported by the provider contract,
            never inferred from icons.
          </p>
        </div>
        <Link className="button-link" to="/onboarding">
          Guided setup
        </Link>
      </div>
      {error && (
        <DataStatusBanner state="unavailable">
          {error.message} Production does not fall back to fixtures.
        </DataStatusBanner>
      )}
      {items?.length === 0 && (
        <DataStatusBanner state="not_configured">
          No supported integration metadata was returned.
        </DataStatusBanner>
      )}
      <div className="integration-grid">
        {items?.map((item) => (
          <article className="panel" key={item.id}>
            <small>{item.category}</small>
            <h2>{item.name}</h2>
            <HealthBadge
              state={
                item.configuration_state === "configured"
                  ? item.connection_state === "connected"
                    ? "healthy"
                    : "warning"
                  : item.configuration_state
              }
            />
            <dl>
              <dt>Support</dt>
              <dd>{item.support_status.replace("_", " ")}</dd>
              <dt>Last collection</dt>
              <dd>
                {item.last_successful_collection
                  ? new Date(item.last_successful_collection).toLocaleString()
                  : "Unknown"}
              </dd>
              <dt>Coverage</dt>
              <dd>{item.coverage == null ? "Unknown" : `${item.coverage}%`}</dd>
              <dt>Required permissions</dt>
              <dd>{item.required_permissions?.join(", ") || "Not supplied"}</dd>
            </dl>
            <Link to={`/integrations/${encodeURIComponent(item.id)}`}>
              Manage integration
            </Link>
          </article>
        ))}
      </div>
    </div>
  );
}
export function IntegrationDetail() {
  const { integrationId } = useParams();
  const { items, error } = useIntegrations();
  const item = items?.find((entry) => entry.id === integrationId);
  if (!items && !error)
    return (
      <div className="page">
        <LoadingSkeleton />
      </div>
    );
  if (!item)
    return (
      <div className="page">
        <h1>Integration unavailable</h1>
        <DataStatusBanner state="unavailable">
          No metadata is available for this integration.
        </DataStatusBanner>
        <Link to="/integrations">Back to catalog</Link>
      </div>
    );
  return (
    <div className="page">
      <div className="eyebrow">INTEGRATIONS / {item.category}</div>
      <h1>{item.name}</h1>
      <p>
        {item.purpose ??
          "Purpose has not been supplied by the integration contract."}
      </p>
      <DataStatusBanner
        state={
          item.configuration_state === "configured"
            ? "healthy"
            : item.configuration_state
        }
      >
        {item.configuration_state.replace("_", " ")}; support:{" "}
        {item.support_status.replace("_", " ")}.
      </DataStatusBanner>
      <div className="content-grid">
        <section className="panel">
          <h2>Collection boundary</h2>
          <h3>Data collected</h3>
          <ul>
            {item.data_collected?.map((value) => (
              <li key={value}>{value}</li>
            )) ?? <li>Not supplied</li>}
          </ul>
          <h3>Data not collected</h3>
          <ul>
            {item.data_not_collected?.map((value) => (
              <li key={value}>{value}</li>
            )) ?? <li>Not supplied</li>}
          </ul>
        </section>
        <section className="panel">
          <h2>Secure setup</h2>
          <dl>
            <dt>Secret handling</dt>
            <dd>
              {item.secret_handling ??
                "Backend-managed references only; resolved secrets are never displayed."}
            </dd>
            <dt>Network access</dt>
            <dd>{item.network_access?.join(", ") || "Not supplied"}</dd>
            <dt>Frequency</dt>
            <dd>{item.collection_frequency ?? "Not supplied"}</dd>
          </dl>
          {item.documentation_url && (
            <a href={item.documentation_url} rel="noreferrer">
              Provider documentation
            </a>
          )}
        </section>
      </div>
    </div>
  );
}
