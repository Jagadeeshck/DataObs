import { useEffect, useRef, useState } from "react";
import cytoscape from "cytoscape";
import { topologyFixture } from "../../test/fixtures";
import type { TopologyNode } from "../../api/types";
import { EntityDrawer } from "../entity-drawer/EntityDrawer";
const colors = {
  healthy: "#35d49a",
  warning: "#f4bd45",
  critical: "#fa5b68",
  unknown: "#8492a6",
};
export function FlowMap() {
  const graph = useRef<HTMLDivElement>(null);
  const cyRef = useRef<cytoscape.Core>();
  const [selected, setSelected] = useState<TopologyNode | null>(null);
  const [overlay, setOverlay] = useState("Incidents");
  const [table, setTable] = useState(false);
  useEffect(() => {
    if (!graph.current) return;
    const nodes = topologyFixture.nodes.map((n) => ({
      data: { ...n, label: n.name },
    }));
    const edges = topologyFixture.edges.map((e) => ({
      data: {
        ...e,
        source: e.source_node_id,
        target: e.destination_node_id,
      },
    }));
    const cy = cytoscape({
      container: graph.current,
      elements: [...nodes, ...edges],
      layout: { name: "breadthfirst", directed: true, spacingFactor: 1.45 },
      style: [
        {
          selector: "node",
          style: {
            "background-color": (e) =>
              colors[e.data("health") as keyof typeof colors],
            label: "data(label)",
            "text-valign": "bottom",
            "text-margin-y": 10,
            color: "#dbe7f5",
            "font-size": 12,
            width: 48,
            height: 48,
            "border-width": 6,
            "border-color": (e) =>
              `${colors[e.data("health") as keyof typeof colors]}33`,
          },
        },
        {
          selector: 'node[type="topic"]',
          style: { shape: "round-rectangle", width: 74 },
        },
        { selector: 'node[type="dataset"]', style: { shape: "barrel" } },
        { selector: 'node[type="job"]', style: { shape: "diamond" } },
        {
          selector: "edge",
          style: {
            width: 4,
            "line-color": (e) =>
              colors[e.data("health") as keyof typeof colors] ?? "#66809e",
            "target-arrow-color": (e) =>
              colors[e.data("health") as keyof typeof colors] ?? "#66809e",
            "target-arrow-shape": "triangle",
            "curve-style": "bezier",
            opacity: 0.85,
            "line-style": "solid",
          },
        },
        {
          selector: "edge[confidence < 0.7]",
          style: { opacity: 0.45, "line-style": "dashed" },
        },
        {
          selector: ":selected",
          style: {
            "overlay-color": "#4b8dff",
            "overlay-opacity": 0.22,
            "overlay-padding": 12,
          },
        },
      ],
    });
    cy.on("tap", "node", (event) => {
      const node = topologyFixture.nodes.find(
        (n) => n.id === event.target.id(),
      );
      setSelected(node ?? null);
    });
    cyRef.current = cy;
    return () => cy.destroy();
  }, []);
  return (
    <div className="flow-page">
      <div className="flow-toolbar">
        <div>
          <div className="eyebrow">
            DATA FLOW <span>/</span> LIVE TOPOLOGY
          </div>
          <h1>Live Data Flow</h1>
          <p>
            Observed pathways across sources, streams, jobs and data products.
          </p>
        </div>
        <div className="actions">
          <button onClick={() => cyRef.current?.fit()}>⊙ Fit view</button>
          <button onClick={() => setTable(!table)}>☷ Accessible list</button>
          <button>☆ Save view</button>
        </div>
      </div>
      <div className="flow-controls">
        <label className="search">
          ⌕{" "}
          <input
            aria-label="Search topology"
            placeholder="Search entities, owners or services…"
          />
        </label>
        <label>
          Mode
          <select>
            <option>Current health</option>
            <option>Blast radius</option>
            <option>Root-cause candidates</option>
          </select>
        </label>
        <label>
          Overlay
          <select value={overlay} onChange={(e) => setOverlay(e.target.value)}>
            <option>Incidents</option>
            <option>Freshness & quality</option>
            <option>Kafka lag & retention</option>
            <option>Ownership</option>
          </select>
        </label>
        <button className="filter">◇ All node types</button>
        <button className="filter">● All health states</button>
      </div>
      <div className="graph-frame">
        <div className="graph-meta">
          <span>
            <i className="live-dot" /> LIVE
          </span>
          <b>{topologyFixture.nodes.length} visible nodes</b>
          <b>{topologyFixture.edges.length} observed pathways</b>
          <span>Updated 8s ago</span>
        </div>
        <div
          ref={graph}
          className="graph"
          role="img"
          aria-label="Topology graph showing six entities and five directional pathways"
        />
        <div className="legend">
          <b>Evidence</b>
          <span>
            <i className="solid-line" /> Fully observed
          </span>
          <span>
            <i className="dash-line" /> Partial / inferred
          </span>
          <b>Health</b>
          <span className="good">● Healthy</span>
          <span className="warn">● Warning</span>
          <span className="bad">● Critical</span>
        </div>
        <div className="map-actions">
          <button
            title="Zoom in"
            onClick={() => cyRef.current?.zoom(cyRef.current.zoom() * 1.2)}
          >
            +
          </button>
          <button
            title="Zoom out"
            onClick={() => cyRef.current?.zoom(cyRef.current.zoom() * 0.8)}
          >
            −
          </button>
          <button title="Fit" onClick={() => cyRef.current?.fit()}>
            ⌂
          </button>
        </div>
        {table && (
          <div className="accessible-table">
            <h2>Filtered topology entities</h2>
            <table>
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Type</th>
                  <th>Health</th>
                  <th>Owner</th>
                </tr>
              </thead>
              <tbody>
                {topologyFixture.nodes.map((n) => (
                  <tr key={n.id} tabIndex={0} onClick={() => setSelected(n)}>
                    <td>{n.name}</td>
                    <td>{n.type}</td>
                    <td>{n.health}</td>
                    <td>{n.owner}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
      {selected && (
        <EntityDrawer node={selected} onClose={() => setSelected(null)} />
      )}
      <footer className="flow-footer">
        <div>
          <span className="bad">● Critical pathway</span>
          <b>checkout-api → orders.events.v2 → enrich-orders</b>
        </div>
        <p>
          Retention risk threatens 14 downstream entities.{" "}
          <button onClick={() => setSelected(topologyFixture.nodes[2])}>
            Investigate entity →
          </button>
        </p>
      </footer>
    </div>
  );
}
