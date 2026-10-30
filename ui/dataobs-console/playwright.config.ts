import { defineConfig, devices } from "@playwright/test";

const supportedProjects = [
  { name: "chromium", use: { ...devices["Desktop Chrome"] } },
  { name: "firefox", use: { ...devices["Desktop Firefox"] } },
  { name: "webkit", use: { ...devices["Desktop Safari"] } },
];
const projects =
  process.env.DATAOBS_PLAYWRIGHT_MATRIX === "all"
    ? supportedProjects
    : [supportedProjects[0]];

export default defineConfig({
  testDir: "./e2e",
  use: {
    baseURL: "http://127.0.0.1:4173",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  webServer: {
    command: "pnpm vite preview --host 127.0.0.1",
    port: 4173,
    reuseExistingServer: true,
  },
  projects,
});
