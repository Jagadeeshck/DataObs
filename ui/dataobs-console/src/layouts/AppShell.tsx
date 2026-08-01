import { NavLink, Outlet } from "react-router-dom";
import { useProductContext } from "../state/context";
const future = [
  "Pipelines",
  "Incidents",
  "Automation",
  "Integrations",
  "Administration",
];
export function AppShell() {
  const { tenant, environment, setTenant, setEnvironment } =
    useProductContext();
  return (
    <div className="app-shell">
      <header>
        <div className="brand">
          <span className="brand-mark">D</span>
          <div>
            <strong>DataObs</strong>
            <small>CONSOLE</small>
          </div>
        </div>
        <div className="context">
          <label>
            Tenant
            <select
              aria-label="Tenant"
              value={tenant}
              onChange={(e) => setTenant(e.target.value)}
            >
              <option value="acme-retail">Acme Retail</option>
              <option value="northstar">Northstar</option>
            </select>
          </label>
          <label>
            Environment
            <select
              aria-label="Environment"
              value={environment}
              onChange={(e) => setEnvironment(e.target.value)}
            >
              <option value="production">Production</option>
              <option value="staging">Staging</option>
            </select>
          </label>
          <label>
            Time range
            <select aria-label="Time range">
              <option>Last 24 hours</option>
              <option>Last 7 days</option>
            </select>
          </label>
          <button className="refresh">↻ 30s</button>
        </div>
        <div className="identity">
          <span className="live-dot" /> Live updates{" "}
          <button aria-label="Help">?</button>
          <span className="avatar">JD</span>
        </div>
      </header>
      <aside>
        <nav aria-label="Primary">
          <NavLink to="/" end>
            ⌁ <span>Command Center</span>
          </NavLink>
          <NavLink to="/flow">
            ⌘ <span>Data Flow</span>
          </NavLink>
          <NavLink to="/pathways">
            ⇄ <span>Pathways</span>
          </NavLink>
          <NavLink to="/assets">
            ◇ <span>Assets</span>
          </NavLink>
          <NavLink to="/streams">
            ≋ <span>Streams</span>
          </NavLink>
          <NavLink to="/data-products">
            ▣ <span>Data Products</span>
          </NavLink>
          <NavLink to="/jobs">
            ▤ <span>Jobs</span>
          </NavLink>
          <NavLink to="/lineage">
            ↝ <span>Lineage</span>
          </NavLink>
          {future.map((x) => (
            <span className="future" key={x}>
              ○ <b>{x}</b>
              <em>Future</em>
            </span>
          ))}
        </nav>
        <div className="coverage">
          <small>COLLECTION COVERAGE</small>
          <strong>94.2%</strong>
          <div>
            <i style={{ width: "94.2%" }} />
          </div>
          <span>
            <i className="live-dot" /> 12 sources reporting
          </span>
        </div>
      </aside>
      <main>
        <Outlet />
      </main>
    </div>
  );
}
