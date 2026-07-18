import { useParams } from "react-router-dom";
export function IncidentDetail() {
  const { incidentId } = useParams();
  return (
    <div className="page incident-page">
      <div className="eyebrow">INCIDENTS / {incidentId}</div>
      <h1>Checkout events retention window at risk</h1>
      <p>
        <span className="severity critical">Critical</span> Open · detected 38
        minutes ago · Order fulfillment
      </p>
      <div className="content-grid">
        <section className="panel">
          <h2>Impact and evidence</h2>
          <p>
            Consumer throughput is below the drain rate required before the
            topic retention boundary. Fourteen downstream entities may receive
            incomplete data.
          </p>
          <dl>
            <div>
              <dt>Suspected root cause</dt>
              <dd>enrich-orders consumer throughput regression</dd>
            </div>
            <div>
              <dt>Blast radius</dt>
              <dd>14 entities · 3 business services</dd>
            </div>
            <div>
              <dt>Case</dt>
              <dd>DATAOBS-481</dd>
            </div>
          </dl>
        </section>
        <section className="panel">
          <h2>Workflow execution</h2>
          <p>
            <b>Safe capacity review</b>
          </p>
          <p>
            Awaiting human approval. No destructive or autonomous action is
            enabled.
          </p>
          <button className="primary">Acknowledge incident</button>
        </section>
      </div>
    </div>
  );
}
