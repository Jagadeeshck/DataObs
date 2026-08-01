export type PermissionPresentation = {
  label: string;
  description: string;
  group: string;
  classification: "read" | "write" | "admin";
  risk: "standard" | "elevated" | "high";
};
const labels: Record<string, [string, string]> = {
  auth: ["Authentication context", "View trusted authentication context."],
  iam: ["Access management", "View or manage canonical role bindings."],
  audit: ["Security audit", "View bounded security audit evidence."],
  platform: ["Platform administration", "Administer the DataObs platform."],
  tenant: ["Tenant administration", "Administer the current trusted tenant."],
};
export function presentPermission(permission: string): PermissionPresentation {
  const [domain, action = "access"] = permission.split(":");
  const known = labels[domain];
  return {
    label: known
      ? `${known[0]} — ${action}`
      : `Canonical permission: ${permission}`,
    description:
      known?.[1] ??
      "No Console presentation metadata is available; the canonical identifier is shown unchanged.",
    group: known?.[0] ?? "Other canonical permissions",
    classification:
      action === "read" ? "read" : action === "admin" ? "admin" : "write",
    risk:
      action === "read"
        ? "standard"
        : domain === "iam" || domain === "platform"
          ? "high"
          : "elevated",
  };
}
