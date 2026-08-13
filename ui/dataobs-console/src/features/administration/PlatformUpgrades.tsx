import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { MetricCard } from "../../components/Evidence";
import { OperationalTable } from "../../visualization";
import {
  authoritativeLabel,
  entryCurrent,
  entryTarget,
  isCompatibilityBlocking,
  isReadinessBlocking,
  isRollbackLimited,
  predecessorStatus,
  upgradeClient,
  type UpgradeSnapshot,
} from "../../platform-operations";
import { AdminPageHeader } from "./Administration";

const defaultTarget = "0.2.0";
export function PlatformUpgrades() {
  const [snapshot, setSnapshot] = useState<UpgradeSnapshot>();
  const [generation, setGeneration] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    upgradeClient
      .snapshot(defaultTarget, controller.signal)
      .then(setSnapshot)
      .catch(() =>
        setSnapshot({ failures: ["compatibility", "upgrade-readiness"] }),
      );
    return () => controller.abort("stale_view");
  }, [generation]);
  const matrix = Object.entries(
    snapshot?.compatibility?.dimensions ?? {},
  ).flatMap(([area, entries]) =>
    entries.map((entry, index) => ({ id: `${area}-${index}`, area, entry })),
  );
  const predecessor = predecessorStatus(snapshot?.compatibility?.dimensions);
  const blockers = snapshot?.readiness?.reason_codes ?? [];
  const migration = snapshot?.compatibility?.dimensions.migration;
  return (
    <section className="admin-page platform-operations upgrade-page">
      <AdminPageHeader title="Upgrades & Compatibility">
        <button onClick={() => setGeneration((value) => value + 1)}>
          Refresh assessment
        </button>
      </AdminPageHeader>
      <nav aria-label="Platform Operations sections" className="platform-tabs">
        <Link to="/administration/platform">Overview and fleet</Link>
        <Link to="/administration/platform/supportability">Supportability</Link>
        <Link to="/administration/platform/readiness">
          Operational Readiness
        </Link>
        <Link to="/administration/platform/upgrades" aria-current="page">
          Upgrades & Compatibility
        </Link>
      </nav>
      <div className="admin-notice" role="note">
        <strong>Assessment only.</strong> DataObs Console does not execute
        platform upgrades from this screen.
      </div>
      {snapshot?.failures.length ? (
        <div className="admin-notice" role="alert">
          <strong>Partial assessment.</strong> Unavailable:{" "}
          {snapshot.failures.join(", ")}. Available evidence remains visible;
          unavailable evidence is unknown.
        </div>
      ) : null}
      {!snapshot ? (
        <p role="status">Loading authoritative upgrade assessment…</p>
      ) : (
        <>
          <div className="metric-grid" aria-label="Upgrade overview">
            <MetricCard
              label="Current platform version"
              value={
                snapshot.readiness?.current ??
                snapshot.compatibility?.dataobs_version
              }
            />
            <MetricCard
              label="Desired / target version"
              value={snapshot.readiness?.target}
            />
            <MetricCard
              label="Upgrade readiness"
              value={authoritativeLabel(snapshot.readiness?.readiness)}
            />
            <MetricCard
              label="Compatibility policy"
              value={authoritativeLabel(snapshot.compatibility?.release_state)}
            />
            <MetricCard
              label="Rollback classification"
              value={authoritativeLabel(
                snapshot.readiness?.rollback_classification,
              )}
            />
            <MetricCard
              label="Migration state"
              value={
                migration?.[0]
                  ? authoritativeLabel(migration[0].state)
                  : "Unknown — not exposed"
              }
            />
            <MetricCard label="Deprecations" value="Unknown — not exposed" />
            <MetricCard
              label="Evidence freshness"
              value="Unknown — timestamp not supplied"
            />
          </div>
          <section
            className="platform-section"
            aria-labelledby="readiness-heading"
          >
            <h2 id="readiness-heading">Upgrade readiness</h2>
            <p className="readiness-headline">
              <strong>
                {authoritativeLabel(snapshot.readiness?.readiness)}
              </strong>
            </p>
            {isReadinessBlocking(snapshot.readiness?.readiness) && (
              <p role="alert">
                The authoritative assessment is blocked. This state is not a
                caution or approval.
              </p>
            )}
            <dl>
              <dt>Source version</dt>
              <dd>{snapshot.readiness?.current ?? "Unknown"}</dd>
              <dt>Target version</dt>
              <dd>{snapshot.readiness?.target ?? "Unknown"}</dd>
              <dt>Source profile</dt>
              <dd>Unknown — not supplied</dd>
              <dt>Destination profile</dt>
              <dd>Unknown — not supplied</dd>
              <dt>Supported predecessor</dt>
              <dd>
                <strong>
                  {predecessor === "supported"
                    ? "Yes"
                    : predecessor === "unknown"
                      ? "Unknown"
                      : "No"}
                </strong>{" "}
                ({authoritativeLabel(predecessor)})
              </dd>
              <dt>Intermediate hops</dt>
              <dd>Not supplied; no path inferred</dd>
            </dl>
          </section>
          <section className="platform-section">
            <h2>Upgrade Blockers</h2>
            {blockers.length ? (
              <ul>
                {blockers.map((code) => (
                  <li key={code}>
                    <strong>{code}</strong> — authoritative readiness reason
                  </li>
                ))}
              </ul>
            ) : (
              <p>
                No blockers were returned. This alone is not production
                approval.
              </p>
            )}
          </section>
          <section className="platform-section">
            <h2>Compatibility matrix</h2>
            <OperationalTable
              caption="Independently reported compatibility policy areas"
              rows={matrix}
              columns={[
                {
                  id: "area",
                  label: "Area",
                  render: (row) => row.area.replaceAll("_", " "),
                },
                {
                  id: "current",
                  label: "Current",
                  render: (row) => entryCurrent(row.entry),
                },
                {
                  id: "target",
                  label: "Target / range",
                  render: (row) => entryTarget(row.entry),
                },
                {
                  id: "result",
                  label: "Result",
                  render: (row) => authoritativeLabel(row.entry.state),
                },
                {
                  id: "blocking",
                  label: "Blocking",
                  render: (row) =>
                    isCompatibilityBlocking(row.entry.state)
                      ? "Yes"
                      : "No (as reported)",
                },
                {
                  id: "evidence",
                  label: "Evidence",
                  render: (row) => row.entry.evidence ?? "Not supplied",
                },
              ]}
            />
          </section>
          <div className="admin-grid">
            <article>
              <h2>Migration graph</h2>
              <dl>
                <dt>Migration count</dt>
                <dd>Unknown — not exposed</dd>
                <dt>Terminal migration</dt>
                <dd>Unknown — not exposed by contract</dd>
                <dt>Graph / collision / dependency integrity</dt>
                <dd>Unknown — not exposed</dd>
                <dt>Immutability</dt>
                <dd>Unknown — evidence not exposed</dd>
              </dl>
              <p>No terminal is guessed or hardcoded.</p>
            </article>
            <article>
              <h2>Deployment Metadata Consistency</h2>
              <dl>
                <dt>Canonical terminal migration</dt>
                <dd>Unknown — not exposed</dd>
                <dt>Helm configured migration</dt>
                <dd>Unknown — not exposed</dd>
                <dt>Validation</dt>
                <dd>Unknown — not exposed</dd>
              </dl>
            </article>
            <article>
              <h2>API Compatibility</h2>
              <p>
                {snapshot.compatibility?.dimensions.openapi
                  ? authoritativeLabel(
                      snapshot.compatibility.dimensions.openapi[0]?.state,
                    )
                  : "Unknown — not evaluated by this response"}
              </p>
            </article>
            <article>
              <h2>Schema Compatibility</h2>
              <p>
                {snapshot.compatibility?.dimensions.schema
                  ? authoritativeLabel(
                      snapshot.compatibility.dimensions.schema[0]?.state,
                    )
                  : "Unknown — not evaluated by this response"}
              </p>
            </article>
            <article>
              <h2>Configuration Compatibility</h2>
              <p>
                {snapshot.compatibility?.dimensions.configuration
                  ? authoritativeLabel(
                      snapshot.compatibility.dimensions.configuration[0]?.state,
                    )
                  : "Unknown — not evaluated by this response"}
              </p>
              <p>Raw configuration is never displayed.</p>
            </article>
            <article>
              <h2>Rollback</h2>
              <p>
                <strong>
                  {authoritativeLabel(
                    snapshot.readiness?.rollback_classification,
                  )}
                </strong>
              </p>
              {isRollbackLimited(
                snapshot.readiness?.rollback_classification,
              ) && (
                <p>
                  Rollback is limited or unvalidated. No procedure is inferred.
                </p>
              )}
              <p>There is no rollback action on this screen.</p>
            </article>
          </div>
          <section className="platform-section">
            <h2>Deprecations</h2>
            <p>
              Deprecation records and applicability metadata are not exposed by
              the current APIs. None are inferred from version strings.
            </p>
          </section>
          <section className="platform-section">
            <h2>Readiness and approval are distinct</h2>
            <table>
              <caption>Independent lifecycle dimensions</caption>
              <tbody>
                <tr>
                  <th>Compatibility policy</th>
                  <td>
                    {authoritativeLabel(snapshot.compatibility?.release_state)}
                  </td>
                </tr>
                <tr>
                  <th>Upgrade readiness</th>
                  <td>{authoritativeLabel(snapshot.readiness?.readiness)}</td>
                </tr>
                <tr>
                  <th>Operational readiness</th>
                  <td>View separately</td>
                </tr>
                <tr>
                  <th>Release decision</th>
                  <td>Unknown — not supplied</td>
                </tr>
                <tr>
                  <th>Certification</th>
                  <td>Unknown — not supplied</td>
                </tr>
              </tbody>
            </table>
            <p>
              <Link to="/administration/platform/readiness">
                View Operational Readiness
              </Link>
            </p>
          </section>
          <section className="platform-section">
            <h2>Authoritative upgrade sequence</h2>
            {snapshot.readiness?.plan?.length ? (
              <ol>
                {snapshot.readiness.plan.map((step) => (
                  <li key={step}>{step}</li>
                ))}
              </ol>
            ) : (
              <p>No ordered steps supplied.</p>
            )}
            <p>These are assessment metadata, not executable controls.</p>
          </section>
        </>
      )}
    </section>
  );
}
