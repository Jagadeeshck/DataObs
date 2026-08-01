import { FormEvent, useEffect, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import {
  pathwaysApi,
  type Bottlenecks,
  type Impact,
  type PathwayDetail,
  type PathwayLatency,
  type PathwaySlo,
  type PathwaySummary,
  type Topology,
} from "../../api/pathways";
import { ApiError } from "../../api/common";
import { useProductContext } from "../../state/context";

const shown = (value: unknown, suffix = "") =>
  value === null || value === undefined || value === ""
    ? "unavailable"
    : `${String(value)}${suffix}`;
const Evidence = ({ value }: { value?: Partial<PathwayDetail> }) => (
  <dl className="pathway-evidence">
    <div>
      <dt>Data status</dt>
      <dd>{shown(value?.data_status)}</dd>
    </div>
    <div>
      <dt>Observed</dt>
      <dd>{shown(value?.observed_at)}</dd>
    </div>
    <div>
      <dt>Confidence</dt>
      <dd>
        {value?.confidence == null
          ? "unavailable"
          : `${Math.round(value.confidence * 100)}%`}
      </dd>
    </div>
    <div>
      <dt>Source coverage</dt>
      <dd>{value?.source_coverage?.join(", ") || "unavailable"}</dd>
    </div>
    <div>
      <dt>Request ID</dt>
      <dd>{shown(value?.request_id)}</dd>
    </div>
  </dl>
);

function Inventory() {
  const { tenant, environment } = useProductContext();
  const [params, setParams] = useSearchParams();
  const [items, setItems] = useState<PathwaySummary[]>([]);
  const [next, setNext] = useState<string | null>(null);
  const [state, setState] = useState("loading");
  const [refresh, setRefresh] = useState(0);
  useEffect(() => {
    const c = new AbortController();
    const filters = {
      search: params.get("search") || undefined,
      health: params.get("health") || undefined,
      classification: params.get("classification") || undefined,
      owner_team: params.get("owner_team") || undefined,
      business_service: params.get("business_service") || undefined,
      truncated: params.has("truncated")
        ? params.get("truncated") === "true"
        : undefined,
      cursor: params.get("cursor") || undefined,
    };
    pathwaysApi
      .inventory(tenant, environment, filters, c.signal)
      .then((r) => {
        setItems(r.items);
        setNext(r.next_cursor);
        setState(r.items.length ? r.data_status : "empty");
      })
      .catch((e) => {
        if (e.name !== "AbortError") setState("error");
      });
    return () => c.abort();
  }, [tenant, environment, params, refresh]);
  const filter = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const p = new URLSearchParams();
    for (const [k, v] of data) if (v) p.set(k, String(v));
    setState("loading");
    setParams(p);
  };
  return (
    <section className="page" aria-labelledby="pathways-title">
      <div className="page-title">
        <div>
          <div className="eyebrow">STREAMS / PATHWAYS</div>
          <h1 id="pathways-title">Pathway inventory</h1>
          <p>
            Durable, tenant-isolated pathway projections. Empty and unavailable
            evidence is never presented as healthy.
          </p>
        </div>
        <button
          onClick={() => {
            setState("loading");
            setRefresh((x) => x + 1);
          }}
        >
          Refresh evidence
        </button>
      </div>
      <form className="investigation-toolbar pathway-filters" onSubmit={filter}>
        <label>
          Search
          <input name="search" defaultValue={params.get("search") || ""} />
        </label>
        <label>
          Health
          <select name="health" defaultValue={params.get("health") || ""}>
            <option value="">All</option>
            <option>healthy</option>
            <option>degraded</option>
            <option>unhealthy</option>
            <option>unknown</option>
          </select>
        </label>
        <label>
          Classification
          <select
            name="classification"
            defaultValue={params.get("classification") || ""}
          >
            <option value="">All</option>
            <option>complete</option>
            <option>partial</option>
          </select>
        </label>
        <label>
          Owner team
          <input
            name="owner_team"
            defaultValue={params.get("owner_team") || ""}
          />
        </label>
        <label>
          Business service
          <input
            name="business_service"
            defaultValue={params.get("business_service") || ""}
          />
        </label>
        <label>
          Truncation
          <select name="truncated" defaultValue={params.get("truncated") || ""}>
            <option value="">All</option>
            <option value="true">Truncated</option>
            <option value="false">Not truncated</option>
          </select>
        </label>
        <button className="primary">Apply filters</button>
      </form>
      {state === "loading" && <p role="status">Loading pathway evidence…</p>}
      {state === "error" && (
        <p role="alert">
          Pathway inventory is unavailable. Retry with Refresh evidence.
        </p>
      )}
      {state === "empty" && (
        <p role="status">No pathway evidence matched these bounded filters.</p>
      )}
      {items.length > 0 && (
        <div className="table-scroll">
          <table>
            <caption>Observed pathway inventory</caption>
            <thead>
              <tr>
                <th>Pathway</th>
                <th>Classification</th>
                <th>Health</th>
                <th>Nodes / edges</th>
                <th>Coverage</th>
                <th>Confidence</th>
                <th>Last observed</th>
                <th>Truncation</th>
                <th>Owner / service</th>
              </tr>
            </thead>
            <tbody>
              {items.map((p) => (
                <tr key={p.pathway_id}>
                  <td>
                    <Link
                      to={`/pathways/${encodeURIComponent(p.pathway_id)}?tab=overview`}
                    >
                      {p.name || p.pathway_id}
                    </Link>
                  </td>
                  <td>{p.classification}</td>
                  <td>{shown(p.health)}</td>
                  <td>
                    {shown(p.node_count ?? p.node_ids?.length)} /{" "}
                    {shown(p.edge_count ?? p.edge_ids?.length)}
                  </td>
                  <td>{p.source_coverage?.join(", ") || "unavailable"}</td>
                  <td>
                    {p.confidence == null
                      ? "unavailable"
                      : `${Math.round(p.confidence * 100)}%`}
                  </td>
                  <td>{shown(p.observed_at ?? p.last_seen)}</td>
                  <td>
                    {p.truncated
                      ? `truncated; ${shown(p.excluded_edge_count)} excluded`
                      : "not truncated"}
                  </td>
                  <td>
                    {shown(p.owner_team)} / {shown(p.business_service)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {next && (
        <button
          onClick={() => {
            const p = new URLSearchParams(params);
            p.set("cursor", next);
            setParams(p);
          }}
        >
          Next page
        </button>
      )}
    </section>
  );
}
const tabs = [
  "overview",
  "topology",
  "latency",
  "bottlenecks",
  "reliability",
  "backlog-retention",
  "impact",
  "compare",
  "evidence",
  "slos",
];
function Investigation({ pathwayId }: { pathwayId: string }) {
  const { tenant, environment } = useProductContext();
  const [params, setParams] = useSearchParams();
  const tab = params.get("tab") || "overview";
  const [detail, setDetail] = useState<PathwayDetail>();
  const [topology, setTopology] = useState<Topology>();
  const [latency, setLatency] = useState<PathwayLatency>();
  const [bottlenecks, setBottlenecks] = useState<Bottlenecks>();
  const [impact, setImpact] = useState<Impact>();
  const [selected, setSelected] = useState<string>();
  const [slos, setSlos] = useState<PathwaySlo[]>([]);
  const [draft, setDraft] = useState(false);
  const [review, setReview] = useState<Record<string, string>>();
  const [message, setMessage] = useState("");
  useEffect(() => {
    const c = new AbortController();
    Promise.all([
      pathwaysApi.detail(tenant, environment, pathwayId, c.signal),
      pathwaysApi.topology(tenant, environment, pathwayId, c.signal),
      pathwaysApi.latency(tenant, environment, pathwayId, c.signal),
      pathwaysApi.bottlenecks(
        tenant,
        environment,
        pathwayId,
        "latency",
        c.signal,
      ),
      pathwaysApi.impact(tenant, environment, pathwayId, c.signal),
      pathwaysApi.slos(tenant, environment, pathwayId, c.signal),
    ])
      .then(([d, t, l, b, i, s]) => {
        setDetail(d);
        setTopology(t);
        setLatency(l);
        setBottlenecks(b);
        setImpact(i);
        setSlos(s.items.filter((x) => x.pathway_id === pathwayId));
      })
      .catch((e) => {
        if (e.name !== "AbortError")
          setMessage("Pathway evidence is unavailable");
      });
    return () => c.abort();
  }, [tenant, environment, pathwayId]);
  const go = (name: string) => {
    const p = new URLSearchParams(params);
    p.set("tab", name);
    setParams(p);
  };
  const submitSlo = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const f = Object.fromEntries(
      new FormData(e.currentTarget).entries(),
    ) as Record<string, string>;
    if (
      !f.metric ||
      !(Number(f.objective) > 0 && Number(f.objective) <= 100) ||
      !/^\d+[mhd]$/.test(f.evaluation_window)
    ) {
      setMessage(
        "Metric, objective (0–100), and bounded window such as 15m are required.",
      );
      return;
    }
    setReview(f);
  };
  const create = () => {
    if (!review) return;
    pathwaysApi
      .createSlo(tenant, environment, {
        ...review,
        pathway_id: pathwayId,
        objective: Number(review.objective),
        enabled: false,
      })
      .then((r) => {
        setSlos((x) => [...x, r.value]);
        setReview(undefined);
        setDraft(false);
        setMessage("SLO draft created. Runtime evaluation is not asserted.");
      })
      .catch((e) =>
        setMessage(
          e instanceof ApiError && e.status === 412
            ? "SLO changed elsewhere. Reload evidence before retrying."
            : "SLO draft could not be created.",
        ),
      );
  };
  return (
    <section className="page">
      <Link to="/pathways">← Pathway inventory</Link>
      <div className="page-title">
        <div>
          <h1>{detail?.name || pathwayId}</h1>
          <p>
            {detail?.classification || "unavailable"} pathway · evidence-driven
            investigation
          </p>
        </div>
        <button
          onClick={() => {
            go("slos");
            setDraft(true);
          }}
        >
          Create SLO draft
        </button>
      </div>
      <div
        role="tablist"
        aria-label="Pathway investigation sections"
        className="pathway-tabs"
      >
        {tabs.map((x) => (
          <button
            role="tab"
            aria-selected={tab === x}
            tabIndex={tab === x ? 0 : -1}
            key={x}
            onClick={() => go(x)}
          >
            {x.replace("-", " & ")}
          </button>
        ))}
      </div>
      {message && (
        <p role="status" className="notice">
          {message}
        </p>
      )}
      {tab === "overview" && (
        <section>
          <h2>Overview</h2>
          <Evidence value={detail} />
          <dl className="pathway-evidence">
            <div>
              <dt>Health</dt>
              <dd>{shown(detail?.health)}</dd>
            </div>
            <div>
              <dt>Classification</dt>
              <dd>{shown(detail?.classification)}</dd>
            </div>
            <div>
              <dt>Nodes / edges</dt>
              <dd>
                {shown(detail?.node_ids?.length)} /{" "}
                {shown(detail?.edge_ids?.length)}
              </dd>
            </div>
            <div>
              <dt>Latency method</dt>
              <dd>
                {shown(latency?.method)}
                {latency?.method === "edge_estimate" &&
                  " (estimated, not end-to-end measured)"}
              </dd>
            </div>
            <div>
              <dt>P95 latency</dt>
              <dd>{shown(latency?.p95_ms, " ms")}</dd>
            </div>
            <div>
              <dt>Active incidents</dt>
              <dd>{shown(impact?.active_incidents.length)}</dd>
            </div>
          </dl>
        </section>
      )}
      {tab === "topology" && (
        <section>
          <h2>Topology investigation graph</h2>
          {detail?.truncated && (
            <p className="notice">
              Truncated pathway: {shown(detail.excluded_edge_count)} edges
              excluded.
            </p>
          )}
          <div className="pathway-graph" aria-label="Directed pathway graph">
            {topology?.nodes.map((n) => (
              <button
                key={n.node_id}
                onClick={() => setSelected(n.node_id)}
                className={`pathway-node ${n.node_type}`}
              >
                {n.name || n.node_id}
                <small>
                  {n.node_type} · {shown(n.health)}
                </small>
              </button>
            ))}
          </div>
          <p>Selected element: {shown(selected)}</p>
          <div className="table-scroll">
            <table>
              <caption>Accessible edge topology</caption>
              <thead>
                <tr>
                  <th>Source</th>
                  <th>Destination</th>
                  <th>Type</th>
                  <th>Health</th>
                  <th>Confidence</th>
                  <th>Latency</th>
                  <th>Lag</th>
                  <th>Retention risk</th>
                  <th>Evidence</th>
                </tr>
              </thead>
              <tbody>
                {topology?.edges.map((e) => (
                  <tr key={e.edge_id} onClick={() => setSelected(e.edge_id)}>
                    <td>{e.source_node_id}</td>
                    <td>{e.destination_node_id}</td>
                    <td>{e.edge_type}</td>
                    <td>{shown(e.health)}</td>
                    <td>{shown(e.confidence)}</td>
                    <td>{shown(e.metrics?.latency_ms)}</td>
                    <td>{shown(e.metrics?.lag_messages)}</td>
                    <td>{shown(e.metrics?.retention_risk)}</td>
                    <td>{shown(e.evidence_refs?.length)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
      {tab === "latency" && (
        <section>
          <h2>Latency</h2>
          <p>
            Method: <strong>{shown(latency?.method)}</strong>.{" "}
            {latency?.method === "edge_estimate" &&
              "Edge estimate; this is not measured end-to-end latency."}
          </p>
          <p>
            P50 {shown(latency?.p50_ms, " ms")} · P95{" "}
            {shown(latency?.p95_ms, " ms")} · P99{" "}
            {shown(latency?.p99_ms, " ms")}
          </p>
          <p>
            Missing segments:{" "}
            {latency?.missing_segments.join(", ") || "none reported"}
          </p>
        </section>
      )}
      {tab === "bottlenecks" && (
        <section>
          <h2>Bottleneck candidates</h2>
          <p>
            Ranked highest observed contribution. Correlation is not a
            root-cause claim.
          </p>
          <ol>
            {bottlenecks?.items.map((x) => (
              <li key={x.edge_id}>
                <button onClick={() => setSelected(x.edge_id)}>
                  {x.edge_id}
                </button>
                : {x.contribution_percentage}% · confidence{" "}
                {shown(x.confidence)} · {x.health_explanation}
              </li>
            ))}
          </ol>
        </section>
      )}
      {(tab === "reliability" || tab === "backlog-retention") && (
        <section>
          <h2>
            {tab === "reliability" ? "Reliability" : "Backlog and retention"}
          </h2>
          <p>
            Unavailable fields remain unavailable; zero-valued measurements
            remain zero.
          </p>
          <Evidence value={detail} />
        </section>
      )}
      {tab === "impact" && (
        <section>
          <h2>Bounded impact relationships</h2>
          {impact?.items.length ? (
            <ul>
              {impact.items.map((x) => (
                <li key={`${x.resource_type}-${x.resource_id}`}>
                  {x.resource_type}: {x.name || x.resource_id} —{" "}
                  {x.classification}
                </li>
              ))}
            </ul>
          ) : (
            <p>No impact evidence was returned.</p>
          )}
        </section>
      )}
      {tab === "compare" && (
        <Compare
          tenant={tenant}
          environment={environment}
          pathwayId={pathwayId}
        />
      )}{" "}
      {tab === "evidence" && (
        <section>
          <h2>Evidence</h2>
          <Evidence value={detail} />
          <p>Warnings: {detail?.warnings?.join("; ") || "none reported"}</p>
          <p>
            Missing inputs:{" "}
            {detail?.missing_inputs?.join(", ") || "none reported"}
          </p>
          <p>
            Reason codes: {detail?.reason_codes?.join(", ") || "none reported"}
          </p>
        </section>
      )}
      {tab === "slos" && (
        <section>
          <h2>Pathway SLO drafts</h2>
          <p>
            These definitions are not described as actively evaluated without
            runtime evidence.
          </p>
          {slos.length ? (
            <ul>
              {slos.map((s) => (
                <li key={s.id}>
                  {s.metric} · {s.objective}% / {s.evaluation_window} ·{" "}
                  {s.enabled ? "enabled" : "disabled"}
                </li>
              ))}
            </ul>
          ) : (
            <p>No SLO definitions exist for this pathway.</p>
          )}
          {draft && !review && (
            <form onSubmit={submitSlo}>
              <label>
                Metric
                <select name="metric" required>
                  <option value="">Select</option>
                  <option value="latency">Latency</option>
                  <option value="reliability">Reliability</option>
                  <option value="backlog">Backlog</option>
                </select>
              </label>
              <label>
                Objective (%)
                <input
                  name="objective"
                  type="number"
                  min="0.01"
                  max="100"
                  step="0.01"
                  required
                />
              </label>
              <label>
                Evaluation window
                <input name="evaluation_window" placeholder="15m" required />
              </label>
              <button>Review SLO draft</button>
            </form>
          )}
          {review && (
            <div role="dialog" aria-labelledby="review-title">
              <h3 id="review-title">Review before creation</h3>
              <p>
                {review.metric}: {review.objective}% over{" "}
                {review.evaluation_window}; initially disabled.
              </p>
              <button onClick={create}>Confirm SLO draft</button>
              <button onClick={() => setReview(undefined)}>Back</button>
            </div>
          )}
        </section>
      )}
    </section>
  );
}
function Compare({
  tenant,
  environment,
  pathwayId,
}: {
  tenant: string;
  environment: string;
  pathwayId: string;
}) {
  const [message, setMessage] = useState("");
  const submit = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const f = new FormData(e.currentTarget),
      start = String(f.get("start")),
      end = String(f.get("end"));
    const days = (Date.parse(end) - Date.parse(start)) / 86400000;
    if (!Number.isFinite(days) || days <= 0 || days > 31) {
      setMessage("Choose an ordered comparison range of no more than 31 days.");
      return;
    }
    pathwaysApi
      .compare(tenant, environment, pathwayId, {
        start,
        end,
        environment,
        baseline: {},
        comparison: {},
      })
      .then((r) =>
        setMessage(
          `${r.warnings.join(". ")}. Unavailable deltas are not calculated.`,
        ),
      )
      .catch(() => setMessage("Comparison unavailable."));
  };
  return (
    <section>
      <h2>Compare bounded windows</h2>
      <form onSubmit={submit}>
        <label>
          Start
          <input name="start" type="datetime-local" required />
        </label>
        <label>
          End
          <input name="end" type="datetime-local" required />
        </label>
        <button>Compare evidence</button>
      </form>
      {message && <p role="status">{message}</p>}
    </section>
  );
}
export function PathwayExplorer() {
  const { pathwayId } = useParams();
  return pathwayId ? <Investigation pathwayId={pathwayId} /> : <Inventory />;
}
