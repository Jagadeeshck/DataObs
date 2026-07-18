import type { TopologyNode } from "../../api/types";
export function EntityDrawer({
  node,
  onClose,
}: {
  node: TopologyNode;
  onClose: () => void;
}) {
  return (
    <aside
      className="drawer"
      role="dialog"
      aria-modal="true"
      aria-labelledby="entity-title"
    >
      <button
        className="close"
        onClick={onClose}
        aria-label="Close entity details"
      >
        ×
      </button>
      <div className={`entity-icon ${node.health}`}>◇</div>
      <small>{node.type.toUpperCase()}</small>
      <h2 id="entity-title">{node.name}</h2>
      <span className={`health ${node.health}`}>● {node.health}</span>
      <section>
        <h3>Why this needs attention</h3>
        <p>
          {node.health === "critical"
            ? "Retention headroom is below the configured safety threshold and downstream freshness is degrading."
            : "Current observations and recent evidence for this entity."}
        </p>
      </section>
      <dl>
        <div>
          <dt>Owner</dt>
          <dd>{node.owner ?? "Unassigned"}</dd>
        </div>
        <div>
          <dt>Business service</dt>
          <dd>{node.business_service ?? "Order fulfillment"}</dd>
        </div>
        <div>
          <dt>Environment</dt>
          <dd>Production</dd>
        </div>
        <div>
          <dt>Evidence confidence</dt>
          <dd>92% · 4 sources</dd>
        </div>
        <div>
          <dt>Upstream / downstream</dt>
          <dd>2 / 14 entities</dd>
        </div>
      </dl>
      <section>
        <h3>Active signals</h3>
        <div className="signal">
          <b>Retention risk</b>
          <span>Critical · 38m</span>
        </div>
        <div className="signal">
          <b>Consumer lag</b>
          <span>184,320 messages</span>
        </div>
      </section>
      <button className="primary">Open incident INC-1042</button>
      <button className="secondary">Open in Kibana ↗</button>
    </aside>
  );
}
