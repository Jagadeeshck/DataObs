import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../../api/client";
import { useProductContext } from "../../state/context";
import {
  capabilityState,
  capabilityStateLabel,
  formatCoverage,
  providerPresentation,
  type MessagingProviderEvidence,
  type MessagingSystem,
} from "../../messaging";

const capabilityColumns = [
  "inventory",
  "throughput",
  "backlog",
  "lag",
  "delivery",
  "retention",
  "dead_letter",
  "reliability",
  "intelligence",
  "pathways",
  "schemas",
  "connectors",
];

function providerStatus(item: MessagingProviderEvidence) {
  if (!item.configured) return "Not configured";
  if (item.runtime_state === "unavailable") return "Unavailable";
  if (item.data_freshness === "stale") return "Stale";
  if (
    ["collecting", "available", "complete"].includes(item.collection_capability)
  )
    return "Collecting";
  return item.runtime_state.replaceAll("_", " ");
}

export function MessagingOverview() {
  const { tenant, environment } = useProductContext();
  const contextKey = `${tenant}\u0000${environment}`;
  const [result, setResult] = useState<{
    key: string;
    items: MessagingProviderEvidence[];
  }>();
  const [selected, setSelected] = useState<MessagingSystem | "all">("all");
  const [failure, setFailure] = useState<{ key: string; message: string }>();
  useEffect(() => {
    const controller = new AbortController();
    api
      .messagingProviders(tenant, environment, controller.signal)
      .then((response) => setResult({ key: contextKey, items: response.items }))
      .catch((cause: unknown) => {
        if (!controller.signal.aborted)
          setFailure({
            key: contextKey,
            message:
              cause instanceof Error
                ? cause.message
                : "Provider evidence is unavailable",
          });
      });
    return () => controller.abort();
  }, [tenant, environment, contextKey]);

  const providers = result?.key === contextKey ? result.items : [];
  const error = failure?.key === contextKey ? failure.message : "";
  const loading = result?.key !== contextKey && !error;

  const visible =
    selected === "all"
      ? providers
      : providers.filter((item) => item.messaging_system === selected);
  const estate = {
    configured: providers.filter((x) => x.configured).length,
    collecting: providers.filter((x) =>
      ["collecting", "available", "complete"].includes(x.collection_capability),
    ).length,
    stale: providers.filter((x) => x.data_freshness === "stale").length,
    unavailable: providers.filter((x) => x.runtime_state === "unavailable")
      .length,
  };
  const partial = Boolean(error) || estate.stale > 0 || estate.unavailable > 0;

  return (
    <section aria-labelledby="messaging-title">
      <h1 id="messaging-title">Messaging</h1>
      <p>
        Provider-aware operational evidence. Capability availability and state
        are negotiated with the server.
      </p>
      {loading && <p role="status">Loading messaging provider evidence…</p>}
      {error && (
        <div role="alert" className="data-state">
          <strong>Messaging evidence is partial.</strong> {error}
        </div>
      )}
      {!loading && providers.length > 0 && (
        <>
          {partial && (
            <p role="status">
              <strong>Messaging evidence is partial.</strong> Review provider
              states below; the estate is not reported healthy.
            </p>
          )}
          <div className="metric-grid" aria-label="Messaging estate summary">
            <article className="metric-card">
              <span>Configured systems</span>
              <strong>{estate.configured}</strong>
            </article>
            <article className="metric-card">
              <span>Collecting evidence</span>
              <strong>{estate.collecting}</strong>
            </article>
            <article className="metric-card">
              <span>Stale systems</span>
              <strong>{estate.stale}</strong>
            </article>
            <article className="metric-card">
              <span>Unavailable systems</span>
              <strong>{estate.unavailable}</strong>
            </article>
          </div>
          <label>
            Messaging system{" "}
            <select
              aria-label="Messaging system"
              value={selected}
              onChange={(event) =>
                setSelected(event.target.value as MessagingSystem | "all")
              }
            >
              <option value="all">All systems</option>
              {providers.map((item) => (
                <option
                  key={item.messaging_system}
                  value={item.messaging_system}
                >
                  {providerPresentation(item.messaging_system).displayName}
                </option>
              ))}
            </select>
          </label>
          <div className="metric-grid" aria-label="Messaging providers">
            {visible.map((item) => {
              const presentation = providerPresentation(item.messaging_system);
              return (
                <article
                  className="page-card"
                  key={item.messaging_system}
                  aria-labelledby={`provider-${item.messaging_system}`}
                >
                  <h2 id={`provider-${item.messaging_system}`}>
                    <span aria-hidden="true">{presentation.mark}</span>{" "}
                    {presentation.displayName}
                  </h2>
                  <dl>
                    <dt>State</dt>
                    <dd>{providerStatus(item)}</dd>
                    <dt>Freshness</dt>
                    <dd>{item.data_freshness.replaceAll("_", " ")}</dd>
                    <dt>Source coverage</dt>
                    <dd>{formatCoverage(item.source_coverage)}</dd>
                    <dt>Last observed</dt>
                    <dd>
                      {item.latest_observation
                        ? new Date(item.latest_observation).toLocaleString()
                        : "No observation"}
                    </dd>
                  </dl>
                  {item.limitations.length > 0 && (
                    <div>
                      <strong>Capability limitations</strong>
                      <ul>
                        {item.limitations.map((limitation) => (
                          <li key={limitation}>{limitation}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {!item.configured && (
                    <Link to="/integrations">Configure integration</Link>
                  )}
                </article>
              );
            })}
          </div>
          <div
            className="table-scroll"
            tabIndex={0}
            aria-label="Scrollable provider capability matrix"
          >
            <table>
              <caption>
                Provider capability matrix — states are server negotiated
              </caption>
              <thead>
                <tr>
                  <th>Provider</th>
                  {capabilityColumns.map((column) => (
                    <th key={column}>{column.replaceAll("_", " ")}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {visible.map((item) => (
                  <tr key={item.messaging_system}>
                    <th>
                      {providerPresentation(item.messaging_system).shortName}
                    </th>
                    {capabilityColumns.map((column) => {
                      const state = capabilityState(item, column);
                      return (
                        <td key={column}>
                          <span
                            className={`capability-state capability-state--${state}`}
                          >
                            {capabilityStateLabel[state]}
                          </span>
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </section>
  );
}
