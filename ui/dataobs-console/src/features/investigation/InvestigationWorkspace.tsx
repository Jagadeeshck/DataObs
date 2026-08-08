import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { buildRoutePath } from "../../app/routes";
import { useProductContext, timeRangeBounds } from "../../state/context";
import {
  parseAnchor,
  safeConsoleReturn,
  investigationPath,
} from "../../investigation/context";
import { InvestigationController } from "../../investigation/registry";
import { investigationProviders } from "../../investigation/providers";
import { togglePin } from "../../investigation/session";
import type {
  InvestigationAnchor,
  InvestigationEvidence,
  InvestigationSnapshot,
} from "../../investigation/types";

export function InvestigationWorkspace() {
  const location = useLocation();
  const navigate = useNavigate();
  const product = useProductContext();
  const anchor = useMemo(
    () => parseAnchor(new URLSearchParams(location.search)),
    [location.search],
  );
  const returnTo = safeConsoleReturn(
    new URLSearchParams(location.search).get("returnTo"),
  );
  const controller = useMemo(
    () => new InvestigationController(investigationProviders),
    [],
  );
  const [snapshot, setSnapshot] = useState<InvestigationSnapshot>();
  const [selected, setSelected] = useState<InvestigationEvidence>();
  const [pins, setPins] = useState<InvestigationAnchor[]>([]);
  const previousScope = useRef(`${product.tenant}:${product.environment}`);
  const [capability, setCapability] = useState("all");
  const [provenance, setProvenance] = useState("all");
  const [state, setState] = useState("all");
  useEffect(() => {
    const scope = `${product.tenant}:${product.environment}`;
    if (scope !== previousScope.current) {
      previousScope.current = scope;
      // eslint-disable-next-line react-hooks/set-state-in-effect -- trusted scope changes must remove prior-scope state immediately
      setPins([]);
      setSnapshot(undefined);
      setSelected(undefined);
    }
    if (!anchor || !product.tenant || document.visibilityState === "hidden")
      return;
    const bounds = timeRangeBounds(product.timeRange);
    void controller.collect(
      {
        anchor,
        tenant: product.tenant,
        environment: product.environment,
        timeRange: product.timeRange,
        ...bounds,
        permissions: product.identity?.permissions ?? [],
      },
      setSnapshot,
    );
    return () => controller.cancel();
  }, [
    anchor,
    controller,
    product.environment,
    product.identity?.permissions,
    product.refreshGeneration,
    product.tenant,
    product.timeRange,
  ]);
  if (!anchor)
    return (
      <section className="page investigation">
        <h1>Investigation workspace</h1>
        <p>
          Select <strong>Investigate</strong> from Global Search or a supported
          entity detail page.
        </p>
        <Link to="/search">Open Global Search</Link>
      </section>
    );
  const evidence = (snapshot?.evidence ?? []).filter(
    (item) =>
      (capability === "all" || item.capabilityId === capability) &&
      (provenance === "all" || item.provenance === provenance) &&
      (state === "all" || item.state === state),
  );
  const detailPath =
    anchor.routeId && anchor.routeParameters
      ? buildRoutePath(anchor.routeId, anchor.routeParameters)
      : undefined;
  return (
    <section className="page investigation">
      <header className="page-header investigation-header">
        <div>
          <p className="eyebrow">Unified investigation</p>
          <h1>{anchor.label ?? anchor.entityType.replaceAll("_", " ")}</h1>
          <p>
            <strong>{anchor.entityType.replaceAll("_", " ")}</strong> ·{" "}
            {product.timeRange} · Tenant and environment inherited from trusted
            Console context.
          </p>
        </div>
        <div className="investigation-actions">
          <button onClick={product.requestRefresh}>Refresh evidence</button>
          <button onClick={() => setPins((items) => togglePin(items, anchor))}>
            {pins.some((p) => p.entityId === anchor.entityId)
              ? "Unpin"
              : "Pin entity"}
          </button>
          {detailPath && <Link to={detailPath}>Open authoritative detail</Link>}
          <button
            onClick={() => (returnTo ? navigate(returnTo) : navigate(-1))}
          >
            Back
          </button>
        </div>
      </header>
      <p className="data-status partial">
        Evidence does not establish causality. Times shown may be event time or
        observation time as labelled.
      </p>
      <section aria-labelledby="provider-heading">
        <h2 id="provider-heading">Evidence summary</h2>
        <p role="status" aria-live="polite">
          {snapshot?.loading
            ? "Providers are loading; partial results are available."
            : `${snapshot?.evidence.length ?? 0} evidence items from bounded providers.`}
        </p>
        <div className="evidence-summary">
          {(snapshot?.providers ?? []).map((p) => (
            <article key={p.providerId}>
              <strong>{p.providerId.replaceAll("-", " ")}</strong>
              <span>
                {p.outcome.replaceAll("_", " ")} · {p.count}
              </span>
            </article>
          ))}
        </div>
      </section>
      <section aria-labelledby="timeline-heading">
        <h2 id="timeline-heading">Unified evidence timeline</h2>
        <div className="investigation-filters">
          <label>
            Capability{" "}
            <select
              value={capability}
              onChange={(e) => setCapability(e.target.value)}
            >
              <option value="all">All</option>
              {[
                ...new Set(
                  (snapshot?.evidence ?? []).map((x) => x.capabilityId),
                ),
              ].map((x) => (
                <option key={x}>{x}</option>
              ))}
            </select>
          </label>
          <label>
            Provenance{" "}
            <select
              value={provenance}
              onChange={(e) => setProvenance(e.target.value)}
            >
              <option value="all">All</option>
              {[
                ...new Set((snapshot?.evidence ?? []).map((x) => x.provenance)),
              ].map((x) => (
                <option key={x}>{x}</option>
              ))}
            </select>
          </label>
          <label>
            State{" "}
            <select value={state} onChange={(e) => setState(e.target.value)}>
              <option value="all">All</option>
              {[...new Set((snapshot?.evidence ?? []).map((x) => x.state))].map(
                (x) => (
                  <option key={x}>{x}</option>
                ),
              )}
            </select>
          </label>
        </div>
        {!snapshot?.loading && !evidence.length && (
          <p>
            No findings observed in selected range. This is not a health
            assertion.
          </p>
        )}
        <ol className="evidence-timeline" aria-label="Evidence timeline">
          {evidence.map((item) => (
            <li key={item.key}>
              <button onClick={() => setSelected(item)}>
                <time dateTime={item.effectiveAt ?? item.observedAt}>
                  {item.effectiveAt
                    ? `Event ${new Date(item.effectiveAt).toLocaleString()}`
                    : item.observedAt
                      ? `Observed ${new Date(item.observedAt).toLocaleString()}`
                      : "Timestamp unavailable"}
                </time>
                <strong>{item.title}</strong>
                <span>
                  {item.capabilityId} · {item.type.replaceAll("_", " ")} ·{" "}
                  {item.state} · provenance: {item.provenance}
                  {item.severity ? ` · severity: ${item.severity}` : ""}
                </span>
              </button>
            </li>
          ))}
        </ol>
      </section>
      <section aria-labelledby="related-heading">
        <h2 id="related-heading">Established relationships</h2>
        {!snapshot?.related.length ? (
          <p>No supported relationships returned.</p>
        ) : (
          <table>
            <caption>
              Accessible investigation graph alternative; depth 1, maximum 50
              nodes and 100 edges.
            </caption>
            <thead>
              <tr>
                <th>Entity</th>
                <th>Type</th>
                <th>Relationship</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {snapshot.related.map((item) => (
                <tr key={item.key}>
                  <td>{item.label ?? item.entityType.replaceAll("_", " ")}</td>
                  <td>{item.entityType}</td>
                  <td>{item.relation.replaceAll("_", " ")}</td>
                  <td>
                    <Link
                      to={investigationPath(
                        item,
                        location.pathname + location.search,
                      )}
                    >
                      Investigate
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
      {pins.length > 0 && (
        <section>
          <h2>Pinned comparison ({pins.length}/5)</h2>
          <ul>
            {pins.map((pin) => (
              <li key={`${pin.entityType}:${pin.entityId}`}>
                {pin.label ?? pin.entityType}
              </li>
            ))}
          </ul>
        </section>
      )}
      {selected && (
        <div
          className="evidence-drawer"
          role="dialog"
          aria-modal="true"
          aria-labelledby="evidence-title"
        >
          <button autoFocus onClick={() => setSelected(undefined)}>
            Close details
          </button>
          <h2 id="evidence-title">{selected.title}</h2>
          <dl>
            <dt>Capability</dt>
            <dd>{selected.capabilityId}</dd>
            <dt>Evidence type</dt>
            <dd>{selected.type}</dd>
            <dt>State</dt>
            <dd>{selected.state}</dd>
            <dt>Provenance</dt>
            <dd>{selected.provenance}</dd>
            {selected.confidence !== undefined && (
              <>
                <dt>Confidence</dt>
                <dd>{selected.confidence}</dd>
              </>
            )}
            {selected.impactScore !== undefined && (
              <>
                <dt>Impact score</dt>
                <dd>{selected.impactScore}</dd>
              </>
            )}
          </dl>
          {selected.routeId && selected.routeParameters && (
            <Link
              to={buildRoutePath(selected.routeId, selected.routeParameters)!}
            >
              Open source page
            </Link>
          )}
          <p>Nearby events are not asserted to be causally related.</p>
        </div>
      )}
    </section>
  );
}
