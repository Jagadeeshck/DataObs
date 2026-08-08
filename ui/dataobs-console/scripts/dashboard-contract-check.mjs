import fs from "node:fs";
const root = new URL("../src/dashboards/", import.meta.url);
const saved = fs.readFileSync(new URL("savedViews.ts", root), "utf8");
const forbidden = [
  "tenantId",
  "environmentId",
  "entityId",
  "incidentId",
  "jobId",
  "runId",
  "apiResponse",
  "accessToken",
];
const found = forbidden.filter((x) => saved.includes(x));
if (found.length) {
  console.error(`Forbidden persisted fields: ${found.join(", ")}`);
  process.exit(1);
}
console.log("dashboard storage privacy and explicit registry checks: pass");
