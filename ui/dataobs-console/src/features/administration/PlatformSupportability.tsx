import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { OperationalTable } from "../../visualization";
import {
  evidenceLabel,
  freshnessPresentation,
  isBlockingState,
  supportabilityClient,
  type SupportabilitySnapshot,
} from "../../platform-operations";
import { AdminPageHeader } from "./Administration";

function State({ value }: { value?: string }) {
  return (
    <strong className="supportability-state">{evidenceLabel(value)}</strong>
  );
}

function PlatformTabs() {
  return (
    <nav aria-label="Platform Operations sections" className="platform-tabs">
      <Link to="/administration/platform">Overview and fleet</Link>
      <Link to="/administration/platform/supportability">Supportability</Link>
      <Link to="/administration/platform/readiness">Operational Readiness</Link>
    </nav>
  );
}

function useSupportability() {
  const [snapshot, setSnapshot] = useState<SupportabilitySnapshot>();
  const [generation, setGeneration] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    const overall = window.setTimeout(
      () => controller.abort("view_timeout"),
      5000,
    );
    supportabilityClient
      .snapshot(controller.signal)
      .then(setSnapshot)
      .catch(() =>
        setSnapshot({
          failures: [
            "support",
            "diagnostics",
            "configuration",
            "maintenance",
            "known-issues",
            "operational-readiness",
          ],
        }),
      );
    return () => {
      window.clearTimeout(overall);
      controller.abort();
    };
  }, [generation]);
  return { snapshot, refresh: () => setGeneration((value) => value + 1) };
}

export function PlatformSupportability() {
  const { snapshot, refresh } = useSupportability();
  const blockers =
    snapshot?.readiness?.categories.filter((gate) =>
      isBlockingState(gate.state),
    ) ?? [];
  return (
    <section className="admin-page platform-operations supportability-page">
      <AdminPageHeader title="Platform Supportability">
        <button onClick={refresh}>Refresh evidence</button>
      </AdminPageHeader>
      <PlatformTabs />
      <p className="admin-lede">
        Evidence first, claims second. Supportability, readiness, release
        decision, certification and runtime health are independent states.
      </p>
      {snapshot?.failures.length ? (
        <div className="admin-notice" role="alert">
          <strong>Supportability evidence is partial.</strong> Unavailable
          sections: {snapshot.failures.join(", ")}.
        </div>
      ) : null}
      {!snapshot ? (
        <p role="status">Loading bounded supportability evidence…</p>
      ) : (
        <>
          <div className="platform-metrics">
            <article>
              <h2>Operational readiness</h2>
              <State value={snapshot.readiness?.state} />
            </article>
            <article>
              <h2>Support profile</h2>
              <State value={snapshot.support?.support_profile} />
            </article>
            <article>
              <h2>Readiness blockers</h2>
              <strong>{blockers.length}</strong>
              <p>authoritative blocking gates</p>
            </article>
            <article>
              <h2>Known issues</h2>
              <strong>{snapshot.knownIssues?.count ?? "Unavailable"}</strong>
              <p>bounded records</p>
            </article>
          </div>
          <div className="admin-grid">
            <article>
              <h2>Support Profile</h2>
              <dl>
                <dt>Overall support</dt>
                <dd>
                  <State value={snapshot.support?.support_profile} />
                </dd>
                <dt>Kubernetes</dt>
                <dd>
                  <State value={snapshot.support?.kubernetes_support_state} />
                </dd>
                <dt>Elasticsearch</dt>
                <dd>
                  <State
                    value={snapshot.support?.elasticsearch_support_state}
                  />
                </dd>
                <dt>OIDC</dt>
                <dd>
                  <State value={snapshot.support?.oidc_support_state} />
                </dd>
                <dt>HA profile</dt>
                <dd>
                  <State value={snapshot.support?.ha_profile} />
                </dd>
                <dt>Freshness</dt>
                <dd>
                  {freshnessPresentation(snapshot.support?.evidence_freshness)}
                </dd>
              </dl>
            </article>
            <article>
              <h2>Readiness hierarchy</h2>
              <dl>
                <dt>Operational readiness</dt>
                <dd>
                  <State value={snapshot.readiness?.state} />
                </dd>
                <dt>Release readiness</dt>
                <dd>
                  <State value={snapshot.support?.release_decision} />
                </dd>
                <dt>Certification</dt>
                <dd>Unknown — not exposed by this API</dd>
                <dt>Runtime health</dt>
                <dd>Not evaluated on this page</dd>
              </dl>
            </article>
            <article>
              <h2>Configuration</h2>
              <dl>
                <dt>Fingerprint</dt>
                <dd>
                  <code>
                    {snapshot.configuration?.fingerprint ??
                      "Unknown — evidence unavailable"}
                  </code>
                </dd>
                <dt>Schema</dt>
                <dd>{snapshot.configuration?.schema_version ?? "Unknown"}</dd>
                <dt>Drift</dt>
                <dd>
                  <State value={snapshot.configuration?.drift_state} />
                </dd>
              </dl>
              <p>Raw configuration is never displayed.</p>
            </article>
            <article>
              <h2>Maintenance</h2>
              <dl>
                <dt>State</dt>
                <dd>
                  <State value={snapshot.maintenance?.state} />
                </dd>
                <dt>Reason</dt>
                <dd>{snapshot.maintenance?.reason_code ?? "Unknown"}</dd>
                <dt>Window</dt>
                <dd>
                  {snapshot.maintenance?.start
                    ? `${snapshot.maintenance.start}–${snapshot.maintenance.expected_end ?? "end unknown"}`
                    : "No maintenance schedule evidence available"}
                </dd>
              </dl>
            </article>
          </div>
          <section className="platform-section">
            <h2>Diagnostics</h2>
            {!snapshot.diagnostics ? (
              <p>Diagnostics unavailable.</p>
            ) : (
              <div className="supportability-cards">
                {snapshot.diagnostics.checks.map((check) => (
                  <article key={check.id}>
                    <h3>{check.id.replaceAll("_", " ")}</h3>
                    <p>
                      <State value={check.state} /> · {check.severity}
                    </p>
                    <p>{check.reason_code}</p>
                    <p>
                      Evidence checked:{" "}
                      {check.checked_at ?? "timestamp not supplied"}
                    </p>
                  </article>
                ))}
              </div>
            )}
          </section>
          <section className="platform-section">
            <h2>Known Issues</h2>
            {!snapshot.knownIssues ? (
              <p>Known issues evidence unavailable.</p>
            ) : snapshot.knownIssues.items.length === 0 ? (
              <p>
                No known-issue records were returned. This is not evidence that
                no issues exist.
              </p>
            ) : (
              <div className="table-scroll">
                <table>
                  <thead>
                    <tr>
                      <th>Issue</th>
                      <th>Severity</th>
                      <th>Status</th>
                      <th>Component</th>
                      <th>Workaround</th>
                      <th>Owner</th>
                    </tr>
                  </thead>
                  <tbody>
                    {snapshot.knownIssues.items.map((issue) => (
                      <tr key={issue.issue_id}>
                        <td>{issue.title}</td>
                        <td>{issue.severity}</td>
                        <td>{issue.state}</td>
                        <td>{issue.affected_component}</td>
                        <td>
                          {issue.workaround_reference ? (
                            <a href={issue.workaround_reference}>
                              Open safe reference
                            </a>
                          ) : (
                            "Not supplied"
                          )}
                        </td>
                        <td>{issue.owner_team}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
          <section className="platform-section">
            <h2>Runbook Coverage</h2>
            <p>
              Runbook registry coverage is not exposed through the Console API.
              Existence, validation and rehearsal are therefore not inferred.
            </p>
          </section>
          <section className="platform-section">
            <h2>Support bundle</h2>
            <p>
              Support bundle generation is available through the Team 0
              operational workflow but is not exposed through the Console API.
            </p>
          </section>
        </>
      )}
    </section>
  );
}

export function OperationalReadiness() {
  const { snapshot, refresh } = useSupportability();
  const rows = useMemo(
    () =>
      snapshot?.readiness?.categories.map((gate) => ({
        id: gate.category,
        ...gate,
        blocking: isBlockingState(gate.state) ? "Yes" : "No (as reported)",
        evaluated: "Not supplied",
        source: gate.evidence,
      })) ?? [],
    [snapshot],
  );
  const blockers = rows.filter((row) => row.blocking === "Yes");
  return (
    <section className="admin-page platform-operations supportability-page">
      <AdminPageHeader title="Operational Readiness">
        <button onClick={refresh}>Refresh evidence</button>
      </AdminPageHeader>
      <PlatformTabs />
      <p className="admin-lede">
        The Team 0 response is authoritative. Unknown is not pass, stale is not
        current, and NO_GO is never softened.
      </p>
      {snapshot?.failures.length ? (
        <div className="admin-notice" role="alert">
          <strong>Supportability evidence is partial.</strong> Unavailable
          sections: {snapshot.failures.join(", ")}.
        </div>
      ) : null}
      {!snapshot ? (
        <p role="status">Loading authoritative readiness evidence…</p>
      ) : (
        <>
          <article
            className="readiness-headline"
            aria-labelledby="readiness-state"
          >
            <h2 id="readiness-state">Operational readiness</h2>
            <State value={snapshot.readiness?.state} />
            <p>{freshnessPresentation(snapshot.support?.evidence_freshness)}</p>
          </article>
          <section className="platform-section">
            <h2>Readiness blockers</h2>
            {blockers.length ? (
              <ul>
                {blockers.map((gate) => (
                  <li key={gate.category}>
                    <strong>{gate.category}</strong>:{" "}
                    {evidenceLabel(gate.state)} — {gate.evidence}
                  </li>
                ))}
              </ul>
            ) : (
              <p>
                No blocking gates were returned. This alone does not establish
                readiness.
              </p>
            )}
          </section>
          <section className="platform-section">
            <h2>Readiness gate matrix</h2>
            <OperationalTable
              caption="Authoritative readiness gates"
              rows={rows}
              columns={[
                {
                  id: "category",
                  label: "Gate / category",
                  render: (row) => row.category,
                },
                {
                  id: "state",
                  label: "Status",
                  render: (row) => evidenceLabel(row.state),
                },
                {
                  id: "evidence",
                  label: "Evidence",
                  render: (row) => row.evidence,
                },
                {
                  id: "evaluated",
                  label: "Last evaluated",
                  render: (row) => row.evaluated,
                },
                {
                  id: "blocking",
                  label: "Blocking",
                  render: (row) => row.blocking,
                },
                { id: "source", label: "Source", render: (row) => row.source },
              ]}
            />
          </section>
        </>
      )}
    </section>
  );
}
