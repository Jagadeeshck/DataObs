import { readdirSync, statSync } from "node:fs";
import { join } from "node:path";

const directory = new URL("../dist/assets/", import.meta.url).pathname;
const files = readdirSync(directory).map((name) => ({
  name,
  bytes: statSync(join(directory, name)).size,
}));
const js = files.filter(({ name }) => name.endsWith(".js"));
const css = files.filter(({ name }) => name.endsWith(".css"));
const report = {
  totalJavaScriptBytes: js.reduce((sum, item) => sum + item.bytes, 0),
  largestJavaScriptChunkBytes: Math.max(...js.map((item) => item.bytes)),
  totalCssBytes: css.reduce((sum, item) => sum + item.bytes, 0),
  routeChunkCount: js.length,
};
const budgets = {
  totalJavaScriptBytes: 5_500_000,
  largestJavaScriptChunkBytes: 1_500_000,
  totalCssBytes: 500_000,
  routeChunkCount: 100,
};
console.log(JSON.stringify({ report, budgets }, null, 2));
const failures = Object.entries(budgets).filter(
  ([name, budget]) => report[name] > budget,
);
if (failures.length) {
  console.error(
    `Performance budget exceeded: ${failures.map(([name]) => name).join(", ")}`,
  );
  process.exit(1);
}
