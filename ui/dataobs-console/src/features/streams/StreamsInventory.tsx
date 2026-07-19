import { Link } from "react-router-dom";

export function StreamsInventory() {
  return (
    <section aria-labelledby="streams-title" className="page-card">
      <h1 id="streams-title">Streams Inventory</h1>
      <p>
        Tenant-scoped Kafka topics with measured health, lag, retention risk,
        schemas, connectors, and incidents.
      </p>
      <form role="search">
        <label>
          Search topics <input name="search" type="search" />
        </label>
        <button type="submit">Apply</button>
      </form>
      <div role="status" className="data-state">
        ◌ No measured Stream evidence is available. Values are unknown, not
        zero.
      </div>
      <table>
        <caption>Kafka streams</caption>
        <thead>
          <tr>
            <th>Topic</th>
            <th>Cluster</th>
            <th>Health</th>
            <th>Max lag</th>
            <th>Retention risk</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>
              <Link to="/streams/topics/example">Example topic</Link>
            </td>
            <td>
              <Link to="/streams/clusters/example">Example cluster</Link>
            </td>
            <td>Unknown</td>
            <td>Unknown</td>
            <td>Unknown</td>
          </tr>
        </tbody>
      </table>
      <nav aria-label="Inventory pagination">
        <button disabled>Previous</button>
        <button disabled>Next</button>
      </nav>
    </section>
  );
}
