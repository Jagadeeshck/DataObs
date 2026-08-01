import { useState } from "react";
export function LineageExplorer() {
  const [mode, setMode] = useState("dataset");
  const [depth, setDepth] = useState(3);
  return (
    <section>
      <h1>Lineage Explorer</h1>
      <p>Bounded, evidence-backed upstream and downstream investigation.</p>
      <form>
        <label>
          Root asset <input required />
        </label>
        <label>
          Mode{" "}
          <select value={mode} onChange={(e) => setMode(e.target.value)}>
            <option value="dataset">Dataset</option>
            <option value="column">Column</option>
          </select>
        </label>
        <label>
          Direction{" "}
          <select>
            <option>Upstream</option>
            <option>Downstream</option>
            <option>Both</option>
          </select>
        </label>
        <label>
          Depth{" "}
          <input
            type="number"
            min="1"
            max="10"
            value={depth}
            onChange={(e) => setDepth(Number(e.target.value))}
          />
        </label>
        <button type="submit">Explore</button>
      </form>
      <div role="status">
        <strong>No lineage selected.</strong> Choose a root to render at most
        200 nodes and 500 edges.
      </div>
      <h2>Accessible graph alternative</h2>
      <table>
        <caption>{mode} lineage edges</caption>
        <thead>
          <tr>
            <th>Source</th>
            <th>Relationship</th>
            <th>Target</th>
            <th>Confidence</th>
            <th>Evidence</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td colSpan={5}>No observed edges</td>
          </tr>
        </tbody>
      </table>
    </section>
  );
}
