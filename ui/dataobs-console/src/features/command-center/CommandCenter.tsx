import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { commandFixture } from "../../test/fixtures";
import type { PriorityItem } from "../../api/types";
const labels: Record<string, string> = {
  critical: "Immediate action required",
  warning: "Needs attention",
  healthy: "Operating normally",
  unknown: "Coverage unavailable",
};
export function CommandCenter() {
  const data = commandFixture;
  const navigate = useNavigate();
  const [filter, setFilter] = useState("All pillars");
  const open = (item: PriorityItem) =>
    navigate(
      `/flow?entity=${encodeURIComponent(item.entity)}&overlay=incident`,
    );
  return (
    <div className="page">
      <div className="eyebrow">
        COMMAND CENTER <span>/</span> LIVE OPERATIONS
      </div>
      <div className="page-title">
        <div>
          <h1>Good afternoon, Jagadeesh</h1>
          <p>Here is what needs attention across your data estate.</p>
        </div>
        <div className="actions">
          <button>☆ Save view</button>
          <button>↗ Share</button>
          <button className="primary" onClick={() => navigate("/flow")}>
            Explore data flow →
          </button>
        </div>
      </div>
      <section className="hero">
        <div className="hero-state">
          <div className="pulse-ring">!</div>
          <div>
            <small>OVERALL DATAOBS HEALTH</small>
            <h2>Critical attention required</h2>
            <p>3 critical incidents are affecting 7 business services.</p>
          </div>
        </div>
        <div className="hero-metrics">
          <div>
            <strong>3</strong>
            <span>Critical incidents</span>
          </div>
          <div>
            <strong>7</strong>
            <span>Affected services</span>
          </div>
          <div>
            <strong>94.2%</strong>
            <span>Collection complete</span>
          </div>
          <div>
            <strong>12:42</strong>
            <span>Last refreshed</span>
          </div>
        </div>
      </section>
      <div className="section-head">
        <div>
          <h2>Health across six pillars</h2>
          <p>
            Coverage and operational state, without assuming missing signals are
            healthy.
          </p>
        </div>
        <select
          aria-label="Filter by pillar"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
        >
          <option>All pillars</option>
          <option>Critical only</option>
        </select>
      </div>
      <section className="pillars">
        {data.pillars.map((p) => (
          <button
            key={p.id}
            className={`pillar ${p.health}`}
            onClick={() => navigate(`/flow?pillar=${p.id}`)}
          >
            <div>
              <span className={`health ${p.health}`}>● {p.health}</span>
              <em>{p.trend}</em>
            </div>
            <h3>{p.name}</h3>
            <strong>{p.metric}</strong>
            <p>{labels[p.health]}</p>
            <footer>
              <span>{p.coverage}</span>
              <b>{p.issues ? `${p.issues} issues` : "—"}</b>
            </footer>
          </button>
        ))}
      </section>
      <div className="content-grid">
        <section className="panel queue">
          <div className="section-head">
            <div>
              <h2>Priority work queue</h2>
              <p>Ranked by severity, business impact and blast radius.</p>
            </div>
            <button>View all</button>
          </div>
          <table>
            <thead>
              <tr>
                <th>Problem</th>
                <th>Affected entity</th>
                <th>Owner</th>
                <th>Started</th>
                <th>Severity</th>
                <th>Impact</th>
                <th>Automation</th>
              </tr>
            </thead>
            <tbody>
              {data.priority_items.map((item) => (
                <tr key={item.id} onClick={() => open(item)} tabIndex={0}>
                  <td>
                    <b>{item.problem}</b>
                    <small>{item.id}</small>
                  </td>
                  <td>{item.entity}</td>
                  <td>{item.owner}</td>
                  <td>{item.started}</td>
                  <td>
                    <span className={`severity ${item.severity.toLowerCase()}`}>
                      {item.severity}
                    </span>
                  </td>
                  <td>{item.impact}</td>
                  <td>{item.automation}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
        <section className="panel changes">
          <div className="section-head">
            <div>
              <h2>Recent changes</h2>
              <p>Potential contributing events</p>
            </div>
          </div>
          {data.recent_changes.map((c) => (
            <article key={c.id}>
              <span>↯</span>
              <div>
                <b>{c.title}</b>
                <p>{c.detail}</p>
              </div>
              <time>{c.time}</time>
            </article>
          ))}
          <article>
            <span>⇄</span>
            <div>
              <b>Kafka configuration changed</b>
              <p>orders.events.v2 retention.ms reduced</p>
            </div>
            <time>1h ago</time>
          </article>
        </section>
      </div>
      <div className="data-warning">
        ◐ <b>Partial coverage:</b> AI and cost telemetry are not configured.
        Missing sources are never reported as healthy or zero.{" "}
        <button>Review integrations</button>
      </div>
    </div>
  );
}
