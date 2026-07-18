const tenants = new Set(["acme-retail", "northstar"]);
const environments = new Set(["production", "staging"]);
export function parseContext(search: string) {
  const params = new URLSearchParams(search);
  const tenant = params.get("tenant") ?? "acme-retail";
  const environment = params.get("environment") ?? "production";
  return {
    tenant: tenants.has(tenant) ? tenant : "acme-retail",
    environment: environments.has(environment) ? environment : "production",
  };
}
export function healthLabel(value: string) {
  return (
    (
      {
        healthy: "Operating normally",
        warning: "Needs attention",
        critical: "Immediate action required",
        unknown: "Coverage unavailable",
      } as Record<string, string>
    )[value] ?? "Coverage unavailable"
  );
}
