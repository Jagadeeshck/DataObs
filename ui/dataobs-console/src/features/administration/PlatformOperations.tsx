import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { MetricCard, StatusDistribution } from "../../visualization";
import {
  platformClient,
  stateLabel,
  stateTone,
  driftState,
  capacityState,
  type LifecycleResource,
  type PlatformSnapshot,
  type ResourceKind,
  type OffboardingPreview,
} from "../../platform-operations";
import { AdminPageHeader } from "./Administration";

function Lifecycle({ state }: { state?: string }) {
  return (
    <span className={`platform-state platform-state--${stateTone(state)}`}>
      <span aria-hidden="true">●</span> {stateLabel(state)}
    </span>
  );
}
function Inventory({
  title,
  kind,
  items,
}: {
  title: string;
  kind: ResourceKind;
  items?: LifecycleResource[];
}) {
  return (
    <section className="platform-section" id={`${kind}s`}>
      <h2>{title}</h2>
      {!items ? (
        <p role="status">This inventory is unavailable.</p>
      ) : items.length === 0 ? (
        <p>No {title.toLowerCase()} were returned.</p>
      ) : (
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Name / identifier</th>
                <th>Lifecycle</th>
                <th>Health</th>
                <th>Environment</th>
                <th>Version</th>
                <th>Revision</th>
                <th>Updated</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.id}>
                  <td>
                    <Link
                      to={`/administration/platform/${kind}s/${encodeURIComponent(item.id)}`}
                    >
                      {item.name || item.id}
                    </Link>
                  </td>
                  <td>
                    <Lifecycle state={item.state} />
                  </td>
                  <td>{stateLabel(item.health as string | undefined)}</td>
                  <td>
                    {String(
                      item.environment_id ||
                        item.requested_environment ||
                        "Unknown",
                    )}
                  </td>
                  <td>
                    {String(
                      item.release_version ||
                        item.candidate_version ||
                        item.kubernetes_version ||
                        "Unknown",
                    )}
                  </td>
                  <td>{item.revision}</td>
                  <td>{item.updated_at || "Unknown"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
export function PlatformOperations() {
  const [snapshot, setSnapshot] = useState<PlatformSnapshot>();
  const [generation, setGeneration] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    platformClient
      .snapshot(controller.signal)
      .then(setSnapshot)
      .catch(() =>
        setSnapshot({
          failures: [
            "fleet",
            "environments",
            "installations",
            "clusters",
            "tenants",
            "drift",
            "capacity",
          ],
        }),
      );
    return () => controller.abort();
  }, [generation]);
  const lifecycle = useMemo(() => {
    const states = [
      ...(snapshot?.environments || []),
      ...(snapshot?.installations || []),
      ...(snapshot?.tenants || []),
    ];
    const count = (values: string[]) =>
      states.filter((x) => values.includes(x.state)).length;
    return [
      {
        id: "active",
        label: "Active / ready",
        count: count(["active", "ready"]),
        symbol: "●",
      },
      {
        id: "transitioning",
        label: "Transitioning",
        count: count([
          "requested",
          "provisioning",
          "validating",
          "installing",
          "migrating",
          "upgrading",
        ]),
        symbol: "◆",
      },
      {
        id: "suspended",
        label: "Suspended",
        count: count(["suspended"]),
        symbol: "■",
      },
      {
        id: "offboarding",
        label: "Offboarding",
        count: count(["offboarding", "deleting"]),
        symbol: "▲",
      },
    ];
  }, [snapshot]);
  return (
    <section className="admin-page platform-operations">
      <AdminPageHeader title="Platform Operations">
        <button type="button" onClick={() => setGeneration((x) => x + 1)}>
          Refresh evidence
        </button>
      </AdminPageHeader>
      <p className="admin-lede">
        Observe fleet lifecycle evidence. Planning, approval, execution and
        verification remain governed Team 0 operational handoffs.
      </p>
      {snapshot?.failures.length ? (
        <div className="admin-notice" role="alert">
          <strong>Platform evidence is partial.</strong> Unavailable providers:{" "}
          {snapshot.failures.join(", ")}.
        </div>
      ) : null}
      {!snapshot ? (
        <p role="status">Loading bounded platform evidence…</p>
      ) : (
        <>
          <div className="platform-metrics">
            <MetricCard
              label="Environments"
              value={snapshot.fleet?.environments ?? null}
              unit="count"
              detail="Count unavailable until supplied by the fleet contract."
            />
            <MetricCard
              label="Installations"
              value={
                snapshot.fleet?.installations ??
                snapshot.fleet?.items?.length ??
                null
              }
              unit="count"
            />
            <MetricCard
              label="Clusters"
              value={snapshot.fleet?.clusters ?? null}
              unit="count"
              detail="Count unavailable until supplied by the fleet contract."
            />
            <MetricCard
              label="Tenants"
              value={snapshot.fleet?.tenants ?? null}
              unit="count"
              detail="Count unavailable until supplied by the fleet contract."
            />
          </div>
          <div className="admin-grid">
            <article>
              <h2>Lifecycle distribution</h2>
              <p>Lifecycle is not health.</p>
              <StatusDistribution
                label="Fleet lifecycle states"
                items={lifecycle}
              />
            </article>
            <article>
              <h2>Configuration Drift</h2>
              <dl>
                <dt>Evidence records</dt>
                <dd>{snapshot.drift?.length ?? "Unavailable"}</dd>
                <dt>Drift detected</dt>
                <dd>
                  {snapshot.drift?.filter(
                    (x) => driftState(x.drift_state) === "drift_detected",
                  ).length ?? "Unknown"}
                </dd>
                <dt>Not evaluated / unknown</dt>
                <dd>
                  {snapshot.drift?.filter((x) =>
                    ["not_evaluated", "unknown"].includes(
                      driftState(x.drift_state),
                    ),
                  ).length ?? "Unknown"}
                </dd>
              </dl>
            </article>
            <article>
              <h2>Capacity</h2>
              <dl>
                <dt>Capacity status</dt>
                <dd>
                  <Lifecycle state={capacityState(snapshot.capacity?.state)} />
                </dd>
                <dt>Reference</dt>
                <dd>{snapshot.capacity?.profiles_reference || "Unknown"}</dd>
              </dl>
              <p>
                Capacity evidence is informational unless the API explicitly
                reports validated.
              </p>
            </article>
            <article>
              <h2>Release readiness</h2>
              <p>
                <strong>Unavailable.</strong> Release readiness data is not
                exposed by the platform lifecycle API.
              </p>
            </article>
          </div>
          <Inventory
            title="Environments"
            kind="environment"
            items={snapshot.environments}
          />
          <Inventory
            title="Installations"
            kind="installation"
            items={snapshot.installations}
          />
          <Inventory
            title="Clusters"
            kind="cluster"
            items={snapshot.clusters}
          />
          <Inventory
            title="Tenant lifecycle"
            kind="tenant"
            items={snapshot.tenants}
          />
          <section className="platform-section" id="drift">
            <h2>Configuration Drift</h2>
            {snapshot.drift?.length ? (
              <div className="table-scroll">
                <table>
                  <thead>
                    <tr>
                      <th>Resource</th>
                      <th>Environment</th>
                      <th>Desired fingerprint</th>
                      <th>Observed fingerprint</th>
                      <th>Classification</th>
                      <th>Evidence</th>
                    </tr>
                  </thead>
                  <tbody>
                    {snapshot.drift.map((x, i) => (
                      <tr key={`${x.resource_id || "evidence"}-${i}`}>
                        <td>{x.resource_type || "Unknown"}</td>
                        <td>{x.environment_id || "Unknown"}</td>
                        <td>
                          <code>{x.desired_state_hash || "Unknown"}</code>
                        </td>
                        <td>
                          <code>{x.observed_state_hash || "Unknown"}</code>
                        </td>
                        <td>
                          <Lifecycle state={driftState(x.drift_state)} />
                        </td>
                        <td>{x.evidence_state || "Unknown"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p>
                No authoritative drift evidence was returned. This does not mean
                no drift.
              </p>
            )}
          </section>
        </>
      )}
    </section>
  );
}

export function PlatformResource360() {
  const { resourceKind = "", resourceId = "" } = useParams();
  const singular = resourceKind.endsWith("s")
    ? resourceKind.slice(0, -1)
    : resourceKind;
  const [resource, setResource] = useState<LifecycleResource>();
  const [error, setError] = useState(false);
  const [preview, setPreview] = useState<OffboardingPreview>();
  useEffect(() => {
    const controller = new AbortController();
    platformClient
      .resource(singular, resourceId, controller.signal)
      .then(setResource)
      .catch(() => setError(true));
    return () => controller.abort();
  }, [singular, resourceId]);
  return (
    <section className="admin-page platform-operations">
      <AdminPageHeader title={`${stateLabel(singular)} 360`} />
      <p>
        <Link to="/administration/platform">← Platform Operations</Link>
      </p>
      {error ? (
        <p role="alert">
          This resource is unavailable or you do not have permission to view it.
        </p>
      ) : !resource ? (
        <p role="status">Loading authoritative metadata…</p>
      ) : (
        <>
          <div className="admin-grid">
            <article>
              <h2>Overview</h2>
              <dl>
                <dt>Identity</dt>
                <dd>{resource.name || resource.id}</dd>
                <dt>Lifecycle</dt>
                <dd>
                  <Lifecycle state={resource.state} />
                </dd>
                <dt>Health</dt>
                <dd>{stateLabel(resource.health as string | undefined)}</dd>
                <dt>Revision</dt>
                <dd>{resource.revision}</dd>
              </dl>
            </article>
            <article>
              <h2>Assignment</h2>
              <dl>
                <dt>Environment</dt>
                <dd>
                  {String(
                    resource.environment_id ||
                      resource.requested_environment ||
                      "Unknown",
                  )}
                </dd>
                <dt>Installation</dt>
                <dd>{String(resource.installation_id || "Unknown")}</dd>
                <dt>Cluster</dt>
                <dd>{String(resource.cluster_id || "Unknown")}</dd>
              </dl>
            </article>
            <article>
              <h2>Version and drift</h2>
              <dl>
                <dt>Version</dt>
                <dd>
                  {String(
                    resource.release_version ||
                      resource.candidate_version ||
                      resource.kubernetes_version ||
                      "Unknown",
                  )}
                </dd>
                <dt>Desired</dt>
                <dd>
                  <code>
                    {String(resource.desired_state_hash || "Unknown")}
                  </code>
                </dd>
                <dt>Observed</dt>
                <dd>
                  <code>
                    {String(resource.observed_state_hash || "Unknown")}
                  </code>
                </dd>
                <dt>Drift</dt>
                <dd>
                  <Lifecycle
                    state={driftState(
                      String(
                        resource.drift_state || resource.drift || "unknown",
                      ),
                    )}
                  />
                </dd>
              </dl>
            </article>
            <article>
              <h2>Operations</h2>
              <p>
                This console is read-first. Plan, approve, execute and verify
                through Team 0-owned governed workflows.
              </p>
            </article>
          </div>
          {singular === "tenant" && (
            <section className="platform-section">
              <h2>Offboarding</h2>
              <p>This preview is read-only and never starts offboarding.</p>
              <button
                type="button"
                onClick={() =>
                  platformClient
                    .offboardingPreview(resource.id)
                    .then(setPreview)
                }
              >
                Open offboarding preview
              </button>
              {preview && (
                <div className="admin-notice" role="status">
                  <h3>Offboarding preview</h3>
                  <dl>
                    <dt>Current revision</dt>
                    <dd>{preview.revision ?? resource.revision}</dd>
                    <dt>Backup required</dt>
                    <dd>
                      {preview.backup_required ? "Yes" : "No / not supplied"}
                    </dd>
                    <dt>Approval required</dt>
                    <dd>
                      {preview.approval_required ? "Yes" : "No / not supplied"}
                    </dd>
                    <dt>Affected resources</dt>
                    <dd>
                      {preview.affected_resources?.length ??
                        preview.resources?.length ??
                        0}
                    </dd>
                    <dt>Blockers</dt>
                    <dd>{preview.blockers?.join(", ") || "None supplied"}</dd>
                    <dt>Warnings</dt>
                    <dd>{preview.warnings?.join(", ") || "None supplied"}</dd>
                  </dl>
                </div>
              )}
            </section>
          )}
        </>
      )}
    </section>
  );
}
