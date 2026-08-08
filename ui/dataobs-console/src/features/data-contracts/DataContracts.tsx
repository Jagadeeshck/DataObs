import { Link } from "react-router-dom";

const sample = [
  {
    name: "Orders contract",
    asset: "orders",
    owner: "Data Platform",
    lifecycle: "Active",
    enforcement: "Warn",
    compliance: "Unobserved",
  },
];

export function DataContracts() {
  return (
    <main>
      <header>
        <p>Observe / Schema governance</p>
        <h1>Data Contracts</h1>
        <p>Verify producer promises without blocking the data plane.</p>
        <Link to="/data-contracts/new">Create draft</Link>
      </header>
      <section aria-labelledby="score">
        <h2 id="score">Compliance scorecard</h2>
        <dl>
          <div>
            <dt>Contracts</dt>
            <dd>{sample.length}</dd>
          </div>
          <div>
            <dt>Breaching</dt>
            <dd>0</dd>
          </div>
          <div>
            <dt>Stale</dt>
            <dd>0</dd>
          </div>
        </dl>
      </section>
      <section>
        <h2>Contract inventory</h2>
        <table>
          <caption>Tenant contract compliance and governance state</caption>
          <thead>
            <tr>
              <th>Contract</th>
              <th>Asset</th>
              <th>Owner</th>
              <th>Lifecycle</th>
              <th>Enforcement</th>
              <th>Compliance</th>
            </tr>
          </thead>
          <tbody>
            {sample.map((x) => (
              <tr key={x.name}>
                <td>
                  <Link to="/data-contracts/example">{x.name}</Link>
                </td>
                <td>{x.asset}</td>
                <td>{x.owner}</td>
                <td>{x.lifecycle}</td>
                <td>{x.enforcement}</td>
                <td>{x.compliance}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </main>
  );
}

export function ContractAuthoring() {
  return (
    <main>
      <h1>Create data contract draft</h1>
      <ol>
        <li>Asset</li>
        <li>Schema</li>
        <li>Quality</li>
        <li>Freshness and volume</li>
        <li>Evolution</li>
        <li>Governance</li>
        <li>Validate</li>
        <li>Save draft</li>
      </ol>
      <p>Saving never approves or activates a contract.</p>
    </main>
  );
}
export function Contract360() {
  return (
    <main>
      <h1>Data Contract</h1>
      <nav aria-label="Contract sections">
        Overview · Contract · Schema · Quality · Freshness · Volume · Versions ·
        Evaluations · Violations · Lineage Impact · Jobs · Data Products ·
        History · Evidence
      </nav>
      <h2>Schema</h2>
      <table>
        <caption>Expected and observed schema</caption>
        <thead>
          <tr>
            <th>Column</th>
            <th>Required</th>
            <th>Expected type</th>
            <th>Observed type</th>
            <th>Nullable</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td colSpan={6}>No schema evidence observed</td>
          </tr>
        </tbody>
      </table>
    </main>
  );
}
export function ContractVersion() {
  return (
    <main>
      <h1>Contract version comparison</h1>
      <p>
        Risk describes configuration differences, not observed production
        impact.
      </p>
    </main>
  );
}
