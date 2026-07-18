import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
export default defineConfig({
  plugins: [react()],
  test: { exclude: ["e2e/**", "node_modules/**"] },
  server: { proxy: { "/api": "http://localhost:8000" } },
  build: { sourcemap: false, chunkSizeWarningLimit: 900 },
});
