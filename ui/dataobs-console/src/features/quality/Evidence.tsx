import type { EvidenceStatus } from "../../api/quality";
export function Evidence({
  status,
  timestamp,
  source,
  children,
}: {
  status: EvidenceStatus;
  timestamp?: string;
  source?: string;
  children?: React.ReactNode;
}) {
  return (
    <div className={`quality-evidence evidence-${status}`}>
      <strong>{status.replace("_", " ")}</strong>
      {children}
      <small>
        {timestamp ? `Observed ${timestamp}` : "No observation timestamp"} ·{" "}
        {source ?? "Source unavailable"}
      </small>
    </div>
  );
}
export const shown = (value: unknown) =>
  value === null || value === undefined || value === ""
    ? "Not observed"
    : String(value);
