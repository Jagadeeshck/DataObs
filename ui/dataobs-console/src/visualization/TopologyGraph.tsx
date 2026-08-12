import { useEffect, useRef, useState } from "react";
import type cytoscape from "cytoscape";
import type { TopologyEdge, TopologyNode } from "./types";
import { visualizationLimits } from "./tokens";
export function TopologyGraph({
  nodes,
  edges,
  label,
  truncated = false,
  asOf,
  onSelect,
}: {
  nodes: readonly TopologyNode[];
  edges: readonly TopologyEdge[];
  label: string;
  truncated?: boolean;
  asOf?: number;
  onSelect?: (node: TopologyNode) => void;
}) {
  if (
    nodes.length > visualizationLimits.topologyNodes ||
    edges.length > visualizationLimits.topologyEdges
  )
    throw new Error("Topology exceeds bounded rendering contract");
  const host = useRef<HTMLDivElement>(null),
    [focused, setFocused] = useState(0);
  useEffect(() => {
    let disposed = false,
      cy: cytoscape.Core | undefined;
    void import("cytoscape").then(({ default: cytoscape }) => {
      if (disposed || !host.current) return;
      cy = cytoscape({
        container: host.current,
        elements: [
          ...nodes.map((n) => ({
            data: { id: n.id, label: n.label, kind: n.kind },
          })),
          ...edges.map((e) => ({
            data: {
              id: e.id,
              source: e.source,
              target: e.target,
              label: e.label ?? "relationship",
            },
          })),
        ],
        layout: { name: "breadthfirst", animate: false },
        style: [
          {
            selector: "node",
            style: {
              label: "data(label)",
              "background-color": "#536dfe",
              "font-size": 10,
            },
          },
          {
            selector: "edge",
            style: {
              label: "data(label)",
              "line-color": "#78909c",
              "target-arrow-shape": "triangle",
              "target-arrow-color": "#78909c",
              "curve-style": "bezier",
            },
          },
        ],
      });
      cy.on("tap", "node", (event: cytoscape.EventObject) => {
        const node = nodes.find((n) => n.id === event.target.id());
        if (node) onSelect?.(node);
      });
    });
    return () => {
      disposed = true;
      cy?.destroy();
    };
  }, [nodes, edges, onSelect]);
  const key = (e: React.KeyboardEvent) => {
    if (e.key !== "ArrowDown" && e.key !== "ArrowUp" && e.key !== "Enter")
      return;
    e.preventDefault();
    const next =
      e.key === "ArrowDown"
        ? Math.min(nodes.length - 1, focused + 1)
        : e.key === "ArrowUp"
          ? Math.max(0, focused - 1)
          : focused;
    setFocused(next);
    if (e.key === "Enter" && nodes[next]) onSelect?.(nodes[next]);
  };
  return (
    <figure className="viz-topology">
      <div ref={host} className="viz-topology__canvas" aria-hidden="true" />
      <figcaption>
        <strong>{label}</strong>
        {truncated && (
          <p role="status">
            Truncated graph: this bounded view does not represent full coverage.
          </p>
        )}
        {asOf && <p>Snapshot as of {new Date(asOf).toISOString()}</p>}
        <table onKeyDown={key}>
          <caption>
            Accessible relationship table. Use up/down arrows and Enter to
            select nodes.
          </caption>
          <thead>
            <tr>
              <th>From</th>
              <th>Relationship</th>
              <th>To</th>
              <th>Confidence</th>
            </tr>
          </thead>
          <tbody>
            {edges.map((e) => (
              <tr key={e.id}>
                <td>
                  {nodes.find((n) => n.id === e.source)?.label ?? e.source}
                </td>
                <td>{e.label ?? "related to"}</td>
                <td>
                  {nodes.find((n) => n.id === e.target)?.label ?? e.target}
                </td>
                <td>{e.confidence ?? "Not supplied"}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <ul className="sr-only">
          {nodes.map((n, i) => (
            <li key={n.id}>
              <button
                tabIndex={i === focused ? 0 : -1}
                onClick={() => onSelect?.(n)}
              >
                {n.label}, {n.kind}
              </button>
            </li>
          ))}
        </ul>
      </figcaption>
    </figure>
  );
}
