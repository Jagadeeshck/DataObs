import { useEffect, useRef, useState } from "react";
import cytoscape from "cytoscape";
import type { Topology, TopologyNode } from "../../api/types";
import { EntityDrawer } from "../entity-drawer/EntityDrawer";
import { api, ApiError } from "../../api";
import { useProductContext } from "../../state/context";
import { useAbortableRequest } from "../../hooks/useAbortableRequest";
import {
  DataStatusBanner,
  ErrorState,
  LoadingSkeleton,
} from "../../components/Evidence";
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
  const [topology, setTopology] = useState<Topology>();
  const [error, setError] = useState<Error>();
  const { tenant, environment, refreshGeneration } = useProductContext();
  const request = useAbortableRequest();
  useEffect(() => {
    if (!tenant || !environment) return;
    // eslint-disable-next-line react-hooks/set-state-in-effect -- reset belongs to this external request generation
    setError(undefined);
    void request((signal) => api.topology(tenant, environment, signal))
      .then(setTopology)
      .catch((reason: unknown) => {
        if ((reason as Error).name !== "AbortError") setError(reason as Error);
      });
  }, [tenant, environment, refreshGeneration, request]);
  useEffect(() => {
    if (!graph.current || !topology) return;
    const nodes = topology.nodes.map((n) => ({
      data: { ...n, label: n.name },
    }));
    const edges = topology.edges.map((e) => ({
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
            "line-style": (e) =>
              e.data("evidence_state") === "observed" ? "solid" : "dashed",
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
      const node = topology.nodes.find((n) => n.id === event.target.id());
      setSelected(node ?? null);
    });
    cyRef.current = cy;
    return () => cy.destroy();
  }, [topology]);
  if (!topology && !error)
    return (
      <div className="page">
        <LoadingSkeleton label="Loading bounded topology evidence…" />
      </div>
    );
  if (!topology && error)
    return (
      <div className="page">
        <h1>Data Flow</h1>
        <ErrorState
          message="Canonical topology evidence is unavailable."
          requestId={error instanceof ApiError ? error.requestId : undefined}
        />
      </div>
    );
  if (!topology) return null;
  return (
    <div className="flow-page">
      <div className="flow-toolbar">
        <div>
          <div className="eyebrow">
            DATA FLOW <span>/</span> EVIDENCE TOPOLOGY
          </div>
          <h1>Unified Data Flow</h1>
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
        {topology.truncated && (
          <DataStatusBanner state="partial">
            Topology was truncated at the bounded API limit (1,000 nodes / 2,500
            edges). Refine filters to inspect omitted evidence.
          </DataStatusBanner>
        )}
        {!topology.data_status.complete && (
          <DataStatusBanner state="partial">
            {topology.data_status.warnings.join(" · ") ||
              "Topology has partial evidence."}
          </DataStatusBanner>
        )}
        <div className="graph-meta">
          <b>{topology.nodes.length} visible nodes</b>
          <b>{topology.edges.length} bounded pathways</b>
          <span>
            {topology.data_status.observed_at
              ? `Observed ${new Date(topology.data_status.observed_at).toLocaleString()}`
              : "Observation time unknown"}
          </span>
        </div>
        <div
          ref={graph}
          className="graph"
          role="img"
          aria-label={`Topology graph showing ${topology.nodes.length} entities and ${topology.edges.length} directional pathways`}
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
                {topology.nodes.map((n) => (
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
        <p>
          {topology.nodes.length} entities and {topology.edges.length}{" "}
          relationships are rendered. Solid edges are observed; dashed edges are
          derived, inferred, partial, unknown, or stale.
        </p>
      </footer>
    </div>
  );
}
