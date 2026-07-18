import { FormEvent, useMemo, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api, PathwayRoute } from "../../api/client";
import { useProductContext } from "../../state/context";

export function PathwayExplorer() {
  const { tenant, environment } = useProductContext();
  const [params, setParams] = useSearchParams();
  const [start, setStart] = useState(params.get("start") ?? "");
  const [end, setEnd] = useState(params.get("end") ?? "");
  const [direction, setDirection] = useState<"downstream" | "upstream">(
    (params.get("direction") as "downstream" | "upstream") ?? "downstream",
  );
  const [maxHops, setMaxHops] = useState(Number(params.get("hops") ?? 6));
  const [result, setResult] = useState<Awaited<
    ReturnType<typeof api.pathwaySearch>
  > | null>(null);
  const [selected, setSelected] = useState<PathwayRoute | null>(null);
  const [status, setStatus] = useState("Select entities to begin");
  const activeRequest = useRef<AbortController | null>(null);
  const routes = useMemo(
    () =>
      result
        ? [
            result.best_path,
            ...result.alternative_paths,
            ...result.partial_paths,
          ].filter((route): route is PathwayRoute => Boolean(route))
        : [],
    [result],
  );
  const submit = (event: FormEvent) => {
    event.preventDefault();
    activeRequest.current?.abort();
    const controller = new AbortController();
    activeRequest.current = controller;
    setParams({
      start,
      ...(end ? { end } : {}),
      direction,
      hops: String(maxHops),
    });
    setStatus("Searching Elasticsearch projections…");
    void api
      .pathwaySearch(
        tenant,
        environment,
        {
          start_node_id: start,
          ...(end ? { end_node_id: end } : {}),
          direction,
          max_hops: maxHops,
          max_paths: 20,
          minimum_confidence: 0,
          include_partial: true,
          active_only: true,
        },
        controller.signal,
      )
      .then((value) => {
        setResult(value);
        setSelected(value.best_path ?? value.partial_paths[0] ?? null);
        setStatus(
          value.best_path || value.partial_paths.length
            ? ""
            : "No observed route matched these bounds",
        );
      })
      .catch((error) => {
        if (error.name !== "AbortError")
          setStatus("Pathway evidence is unavailable");
      });
  };
  return (
    <section
      className="page investigation-page"
      aria-labelledby="pathway-title"
    >
      <div className="eyebrow">
        DATA FLOW <span>/</span> PATHWAY EXPLORER
      </div>
      <div className="page-title">
        <div>
          <h1 id="pathway-title">Pathway Explorer</h1>
          <p>
            Find deterministic, bounded routes and inspect the evidence behind
            every edge.
          </p>
        </div>
        <button
          disabled={!selected}
          title="Monitor creation requires review and confirmation"
        >
          Create monitor
        </button>
      </div>
      <form className="investigation-toolbar pathway-form" onSubmit={submit}>
        <label>
          Start entity
          <input
            required
            maxLength={512}
            value={start}
            onChange={(e) => setStart(e.target.value)}
          />
        </label>
        <label>
          End entity (optional)
          <input
            maxLength={512}
            value={end}
            onChange={(e) => setEnd(e.target.value)}
          />
        </label>
        <label>
          Direction
          <select
            value={direction}
            onChange={(e) => setDirection(e.target.value as typeof direction)}
          >
            <option value="downstream">Downstream</option>
            <option value="upstream">Upstream</option>
          </select>
        </label>
        <label>
          Maximum hops
          <select
            value={maxHops}
            onChange={(e) => setMaxHops(Number(e.target.value))}
          >
            <option>3</option>
            <option>6</option>
            <option>12</option>
          </select>
        </label>
        <button className="primary">Find pathways</button>
      </form>
      {result?.warnings.map((warning) => (
        <p className="notice" role="status" key={warning}>
          {warning}
        </p>
      ))}
      <div className="investigation-grid">
        <section className="panel">
          <h2>Pathway graph</h2>
          {status ? (
            <p className="graph-empty" role="status">
              {status}
            </p>
          ) : (
            <div
              className="route-graph"
              role="img"
              aria-label={`Selected route with ${selected?.nodes.length} nodes and ${selected?.edges.length} edges`}
            >
              {selected?.nodes.map((node, index) => (
                <div className="graph-stage" key={node.id}>
                  <strong>{node.name}</strong>
                  <small>{node.node_type}</small>
                  {index < (selected?.edges.length ?? 0) && (
                    <span aria-hidden="true">→</span>
                  )}
                </div>
              ))}
            </div>
          )}
          <h3>Accessible ranked route list</h3>
          <table>
            <thead>
              <tr>
                <th>Route</th>
                <th>Kind</th>
                <th>Hops</th>
                <th>Confidence</th>
              </tr>
            </thead>
            <tbody>
              {routes.map((route, index) => (
                <tr
                  key={`${route.id}-${index}`}
                  aria-current={selected?.id === route.id}
                >
                  <td>
                    <button
                      className="route-button"
                      onClick={() => setSelected(route)}
                    >
                      {route.nodes.map((node) => node.name).join(" → ")}
                    </button>
                  </td>
                  <td>{route.complete ? "complete" : "partial"}</td>
                  <td>{route.edges.length}</td>
                  <td>{Math.round(route.confidence * 100)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
        <aside className="panel">
          <h2>Investigation summary</h2>
          <div className="summary-row">
            <strong>Ranked alternatives</strong>
            <span>{Math.max(0, routes.length - 1)}</span>
          </div>
          <div className="summary-row">
            <strong>Ranking score</strong>
            <span>{selected?.rank_score ?? "unknown"}</span>
          </div>
          <div className="summary-row">
            <strong>Latency waterfall</strong>
            <span>not configured</span>
          </div>
          <div className="summary-row">
            <strong>Bottlenecks</strong>
            <span>unknown</span>
          </div>
          <div className="summary-row">
            <strong>Lag &amp; retention</strong>
            <span>unknown</span>
          </div>
          <div className="summary-row">
            <strong>Evidence</strong>
            <span>
              {selected ? `${selected.edges.length} edges` : "unknown"}
            </span>
          </div>
          {selected && (
            <ul className="evidence-list">
              {selected.edges.map((edge) => (
                <li key={edge.id}>
                  {edge.evidence.evidence_type.replaceAll("_", " ")} ·{" "}
                  {Math.round(edge.evidence.confidence * 100)}%
                </li>
              ))}
            </ul>
          )}
        </aside>
      </div>
    </section>
  );
}
