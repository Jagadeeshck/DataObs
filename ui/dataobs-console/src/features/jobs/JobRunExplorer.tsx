import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../../api/client";
import { useProductContext } from "../../state/context";

function EvidenceState({
  loading,
  error,
}: {
  loading: boolean;
  error: string;
}) {
  if (loading) return <p role="status">Loading job and run evidence…</p>;
  if (error) return <p role="alert">Partial data: {error}</p>;
  return null;
}

export function JobsInventory() {
  const { tenant, environment } = useProductContext();
  const [items, setItems] = useState<Record<string, unknown>[]>([]);
  const [search, setSearch] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    const controller = new AbortController();
    api
      .jobs(tenant, environment, search, controller.signal)
      .then((result) => {
        setItems(result.items);
        setError("");
      })
      .catch((reason: Error) => setError(reason.message))
      .finally(() => setLoading(false));
    return () => controller.abort();
  }, [tenant, environment, search]);
  return (
    <section>
      <h1>Jobs</h1>
      <p>Investigate schedules, reliability, quality, and incidents.</p>
      <label>
        Search jobs{" "}
        <input
          value={search}
          onChange={(event) => setSearch(event.target.value)}
        />
      </label>
      <EvidenceState loading={loading} error={error} />
      {!loading && !error && !items.length && (
        <p>No jobs were observed in this time range.</p>
      )}
      <table>
        <caption>Job inventory</caption>
        <thead>
          <tr>
            <th>Job</th>
            <th>Platform</th>
            <th>Owner</th>
            <th>State</th>
            <th>Last run</th>
            <th>Duration</th>
          </tr>
        </thead>
        <tbody>
          {items.map((job) => (
            <tr key={String(job.job_id)}>
              <th>
                <Link to={`/jobs/${String(job.job_id)}`}>
                  {String(job.qualified_name ?? job.job_id)}
                </Link>
              </th>
              <td>{String(job.platform ?? "Unknown")}</td>
              <td>{String(job.owner ?? "Not observed")}</td>
              <td>{String(job.state ?? "Unknown")}</td>
              <td>{String(job.last_seen ?? "Not observed")}</td>
              <td>{String(job.duration_ms ?? "Not observed")}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

export function Job360() {
  const { jobId = "" } = useParams();
  return <Entity360 kind="job" id={jobId} />;
}
export function Run360() {
  const { runId = "" } = useParams();
  return <Entity360 kind="run" id={runId} />;
}
function Entity360({ kind, id }: { kind: "job" | "run"; id: string }) {
  const { tenant, environment } = useProductContext();
  const [data, setData] = useState<Record<string, unknown>>({});
  const [error, setError] = useState("");
  useEffect(() => {
    const controller = new AbortController();
    api
      .entity(tenant, environment, kind, id, controller.signal)
      .then(setData)
      .catch((e: Error) => setError(e.message));
    return () => controller.abort();
  }, [tenant, environment, kind, id]);
  return (
    <section>
      <h1>{kind === "job" ? "Job 360" : "Run 360"}</h1>
      <EvidenceState
        loading={!error && !Object.keys(data).length}
        error={error}
      />
      <dl>
        {Object.entries(data)
          .slice(0, 30)
          .map(([key, value]) => (
            <div key={key}>
              <dt>{key.replaceAll("_", " ")}</dt>
              <dd>
                {typeof value === "object"
                  ? JSON.stringify(value)
                  : String(value ?? "Not observed")}
              </dd>
            </div>
          ))}
      </dl>
      <h2>Evidence visualisations</h2>
      <p>
        Text summary and table alternatives are available for duration, task
        DAG, critical path, quality, incidents, resource use, and lineage.
        Missing values mean not observed, not zero.
      </p>
    </section>
  );
}

export function RunComparison() {
  return (
    <section>
      <h1>Compare runs</h1>
      <p>
        Select two runs from the same job. Comparisons preserve missing evidence
        and never divide by zero.
      </p>
      <form>
        <label>
          Base run <input />
        </label>
        <label>
          Target run <input />
        </label>
        <button type="submit">Compare</button>
      </form>
      <p role="status">
        Choose two runs to view duration, task, stage, critical-path, resource,
        dataset, quality, code, and deployment changes.
      </p>
    </section>
  );
}
