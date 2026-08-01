import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { qualityApi, type MonitorCapability } from "../../api/quality";
import { useProductContext } from "../../state/context";
export function MonitorAuthoring() {
  const { tenant, environment } = useProductContext();
  const navigate = useNavigate();
  const [caps, setCaps] = useState<MonitorCapability[]>([]);
  const [step, setStep] = useState<"edit" | "review">("edit");
  const [error, setError] = useState("");
  const [form, setForm] = useState({
    name: "",
    description: "",
    monitor_type: "",
    asset_id: "",
    connection_ref: "",
    schema_name: "",
    table_name: "",
    columns: "",
    timestamp_column: "",
    interval: "5m",
    timezone: "UTC",
    mode: "fixed",
    minimum: "",
    maximum: "",
    managed_by: "console-user",
    severity: "medium",
    consecutive: "1",
  });
  useEffect(() => {
    const c = new AbortController();
    qualityApi
      .capabilities(tenant, environment, c.signal)
      .then((x) => setCaps(x.data.items.filter((c) => c.executable)))
      .catch((e: Error) => setError(e.message));
    return () => c.abort();
  }, [tenant, environment]);
  const cap = useMemo(
    () => caps.find((x) => x.monitor_type === form.monitor_type),
    [caps, form.monitor_type],
  );
  const set = (k: string, v: string) => setForm((x) => ({ ...x, [k]: v }));
  const required = (x: string) => cap?.target_requirements?.includes(x);
  const payload = () => ({
    id: crypto.randomUUID(),
    name: form.name,
    description: form.description,
    tenant_id: tenant,
    environment,
    monitor_type: form.monitor_type,
    target: {
      asset_id: form.asset_id || undefined,
      source_type: "postgresql",
      connection_ref: form.connection_ref || undefined,
      schema_name: form.schema_name || undefined,
      table_name: form.table_name || undefined,
      columns: form.columns
        .split(",")
        .map((x) => x.trim())
        .filter(Boolean)
        .slice(0, 100),
      timestamp_column: form.timestamp_column || undefined,
      parameters: Object.fromEntries(
        (cap?.required_parameters ?? []).map((x) => [x, "configured"]),
      ),
    },
    selector: { asset_ids: [], field_ids: [], labels: {} },
    schedule: { interval: form.interval, timezone: form.timezone },
    threshold: {
      mode: form.mode,
      ...(form.minimum !== "" ? { minimum: Number(form.minimum) } : {}),
      ...(form.maximum !== "" ? { maximum: Number(form.maximum) } : {}),
    },
    ...(form.mode !== "fixed"
      ? {
          baseline: {
            method: "mad",
            history_points: 168,
            minimum_samples: 12,
            sensitivity: "medium",
            seasonality: [],
          },
        }
      : {}),
    alert: {
      severity: form.severity,
      consecutive_breaches: Number(form.consecutive),
      rca_auto_trigger: false,
    },
    managed_by: form.managed_by,
    state: "draft",
    creation_source: "UI",
  });
  const validate = () => {
    if (!form.name || !cap)
      return "Name and an executable monitor type are required.";
    if (!form.asset_id && (!form.schema_name || !form.table_name))
      return "Provide an asset or schema and table.";
    if (required("timestamp_column") && !form.timestamp_column)
      return "Timestamp column is required.";
    if (
      required("column") &&
      form.columns.split(",").filter(Boolean).length !== 1
    )
      return "Exactly one column is required.";
    for (const x of [form.minimum, form.maximum])
      if (x !== "" && !Number.isFinite(Number(x)))
        return "Thresholds must be finite numbers.";
    return "";
  };
  const submit = async () => {
    try {
      const result = await qualityApi.create(
        tenant,
        environment,
        payload() as never,
      );
      navigate(`/quality/monitors/${encodeURIComponent(result.data.id)}`);
    } catch (e) {
      setError((e as Error).message);
    }
  };
  return (
    <section className="quality-page">
      <nav aria-label="Breadcrumb">
        <Link to="/quality">Quality</Link> /{" "}
        <Link to="/quality/monitors">Monitors</Link> / New
      </nav>
      <h1>Create draft monitor</h1>
      <p>
        Capabilities determine every executable type. Connection references are
        identifiers, never credentials.
      </p>
      {error && <p role="alert">{error}</p>}
      {step === "review" ? (
        <>
          <h2>Review exact definition</h2>
          <pre className="review-json">
            {JSON.stringify(payload(), null, 2)}
          </pre>
          <p>No secret or raw SQL field is accepted.</p>
          <button onClick={() => setStep("edit")}>Back</button>{" "}
          <button className="primary-action" onClick={submit}>
            Create draft
          </button>
        </>
      ) : (
        <form
          className="quality-form"
          onSubmit={(e) => {
            e.preventDefault();
            const x = validate();
            if (x) setError(x);
            else {
              setError("");
              setStep("review");
            }
          }}
        >
          <label>
            Name
            <input
              maxLength={200}
              required
              value={form.name}
              onChange={(e) => set("name", e.target.value)}
            />
          </label>
          <label>
            Description
            <textarea
              maxLength={2000}
              value={form.description}
              onChange={(e) => set("description", e.target.value)}
            />
          </label>
          <label>
            Monitor type
            <select
              required
              value={form.monitor_type}
              onChange={(e) => set("monitor_type", e.target.value)}
            >
              <option value="">Select executable type</option>
              {caps.map((x) => (
                <option value={x.monitor_type} key={x.monitor_type}>
                  {x.display_name ?? x.monitor_type}
                </option>
              ))}
            </select>
          </label>
          <fieldset>
            <legend>Target</legend>
            <label>
              Asset ID
              <input
                value={form.asset_id}
                onChange={(e) => set("asset_id", e.target.value)}
              />
            </label>
            <label>
              Connection reference
              <input
                value={form.connection_ref}
                onChange={(e) => set("connection_ref", e.target.value)}
              />
            </label>
            <label>
              Schema
              <input
                value={form.schema_name}
                onChange={(e) => set("schema_name", e.target.value)}
              />
            </label>
            <label>
              Table
              <input
                value={form.table_name}
                onChange={(e) => set("table_name", e.target.value)}
              />
            </label>
            {(required("column") || required("columns")) && (
              <label>
                Permitted columns (comma separated)
                <input
                  value={form.columns}
                  onChange={(e) => set("columns", e.target.value)}
                />
              </label>
            )}
            {required("timestamp_column") && (
              <label>
                Timestamp column
                <input
                  value={form.timestamp_column}
                  onChange={(e) => set("timestamp_column", e.target.value)}
                />
              </label>
            )}
          </fieldset>
          <label>
            Interval
            <input
              pattern="[1-9][0-9]*(m|h|d)"
              value={form.interval}
              onChange={(e) => set("interval", e.target.value)}
            />
          </label>
          <label>
            Threshold mode
            <select
              value={form.mode}
              onChange={(e) => set("mode", e.target.value)}
            >
              {(cap?.threshold_modes ?? ["fixed"]).map((x) => (
                <option key={x}>{x}</option>
              ))}
            </select>
          </label>
          <label>
            Minimum
            <input
              type="number"
              value={form.minimum}
              onChange={(e) => set("minimum", e.target.value)}
            />
          </label>
          <label>
            Maximum
            <input
              type="number"
              value={form.maximum}
              onChange={(e) => set("maximum", e.target.value)}
            />
          </label>
          <button type="submit">Review definition</button>
        </form>
      )}
    </section>
  );
}
