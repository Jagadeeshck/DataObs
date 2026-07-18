import { FormEvent, useState } from "react";
import { useSearchParams } from "react-router-dom";
export function PathwayExplorer() {
  const [params, setParams] = useSearchParams();
  const [start, setStart] = useState(params.get("start") ?? "");
  const [end, setEnd] = useState(params.get("end") ?? "");
  const [searched, setSearched] = useState(false);
  const submit = (event: FormEvent) => {
    event.preventDefault();
    setParams({ start, ...(end ? { end } : {}) });
    setSearched(true);
  };
  return (
    <section className="page investigation-page">
      <div className="eyebrow">
        DATA FLOW <span>/</span> PATHWAY EXPLORER
      </div>
      <div className="page-title">
        <div>
          <h1>Pathway Explorer</h1>
          <p>
            Find deterministic, bounded routes and inspect the evidence behind
            every edge.
          </p>
        </div>
        <button disabled>Create monitor</button>
      </div>
      <form className="investigation-toolbar pathway-form" onSubmit={submit}>
        <label>
          Start entity
          <input
            required
            value={start}
            onChange={(e) => setStart(e.target.value)}
          />
        </label>
        <label>
          End entity (optional)
          <input value={end} onChange={(e) => setEnd(e.target.value)} />
        </label>
        <label>
          Direction
          <select>
            <option>Downstream</option>
            <option>Upstream</option>
          </select>
        </label>
        <label>
          Maximum hops
          <select>
            <option>6</option>
            <option>3</option>
            <option>12</option>
          </select>
        </label>
        <button className="primary">Find pathways</button>
      </form>
      <div className="investigation-grid">
        <section className="panel">
          <h2>Pathway graph</h2>
          <div
            className="graph-empty"
            role="img"
            aria-label="No pathway selected"
          >
            {searched
              ? "Waiting for Elasticsearch pathway evidence"
              : "Select entities to begin"}
          </div>
          <h3>Accessible route list</h3>
          <p className="notice">
            No route evidence loaded. Structural relationships will be labelled
            separately from pipeline lineage.
          </p>
        </section>
        <aside className="panel">
          <h2>Investigation summary</h2>
          {[
            "Ranked alternatives",
            "Latency waterfall",
            "Bottlenecks",
            "Lag & retention",
            "Incidents & SLOs",
            "Evidence & confidence",
          ].map((item) => (
            <div className="summary-row" key={item}>
              <strong>{item}</strong>
              <span>unknown</span>
            </div>
          ))}
        </aside>
      </div>
    </section>
  );
}
