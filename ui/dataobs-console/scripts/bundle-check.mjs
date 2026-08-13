import { readFileSync, readdirSync } from "node:fs";
import { gzipSync } from "node:zlib";
const dir = "dist/assets";
const bytes = readdirSync(dir)
  .filter((x) => x.endsWith(".js"))
  .reduce((n, x) => n + gzipSync(readFileSync(`${dir}/${x}`)).byteLength, 0);
console.log(`JavaScript bundle (gzip): ${(bytes / 1024).toFixed(1)} KiB`);
if (bytes > 2_000_000) process.exit(1);
