import { readdirSync, statSync } from "node:fs";
import { join } from "node:path";
const dir = "dist/assets";
const bytes = readdirSync(dir)
  .filter((x) => x.endsWith(".js"))
  .reduce((n, x) => n + statSync(join(dir, x)).size, 0);
console.log(`JavaScript bundle: ${(bytes / 1024).toFixed(1)} KiB`);
if (bytes > 2_000_000) process.exit(1);
