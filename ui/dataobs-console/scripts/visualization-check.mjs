import fs from "node:fs";
import path from "node:path";
const root = path.resolve("src/visualization");
const required = [
  "TimeSeries.tsx",
  "MetricCard.tsx",
  "Sparkline.tsx",
  "StatusDistribution.tsx",
  "HealthMatrix.tsx",
  "OperationalHeatmap.tsx",
  "EvidenceTimeline.tsx",
  "RankedList.tsx",
  "OperationalTable.tsx",
  "TopologyGraph.tsx",
  "ChartState.tsx",
];
for (const f of required)
  if (!fs.existsSync(path.join(root, f)))
    throw new Error(`Missing primitive ${f}`);
const source = fs
  .readdirSync(root)
  .filter(
    (f) =>
      /\.(ts|tsx)$/.test(f) && !f.endsWith(".test.tsx") && f !== "testing.ts",
  )
  .map((f) => fs.readFileSync(path.join(root, f), "utf8"))
  .join("\n");
for (const contract of [
  "No observation",
  "Forecast",
  "timeSeriesPointsPerSeries",
  "topologyNodes",
  "Accessible relationship table",
])
  if (!source.includes(contract))
    throw new Error(`Missing visualization contract: ${contract}`);
const fixtureImports = [...source.matchAll(/from ["']\.\/testing["']/g)];
if (fixtureImports.length)
  throw new Error("Production visualization module imports synthetic fixtures");
console.log(`Visualization contracts valid (${required.length} primitives).`);
