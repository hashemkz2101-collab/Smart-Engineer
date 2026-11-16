import path from "node:path";
import { fileURLToPath } from "node:url";

import { defineConfig, devices } from "@playwright/test";

const webRoot = path.dirname(fileURLToPath(import.meta.url));
const host = "127.0.0.1";
const port = process.env.SMART_ENGINEER_WEB_PORT ?? "3000";
const baseURL = `http://${host}:${port}`;

// Browser tests run against the built production server (run `next build` first).
// Chromium only: it covers the desktop and mobile-viewport layouts the shell supports.
export default defineConfig({
  testDir: path.join(webRoot, "e2e"),
  fullyParallel: true,
  forbidOnly: Boolean(process.env.CI),
  retries: 0,
  reporter: [["list"]],
  outputDir: path.join(webRoot, "test-results"),
  use: {
    baseURL,
    locale: "fa-IR",
    trace: "retain-on-failure",
  },
  webServer: {
    command: `node ./node_modules/next/dist/bin/next start --hostname ${host} --port ${port}`,
    cwd: webRoot,
    url: baseURL,
    reuseExistingServer: !process.env.CI,
    timeout: 60_000,
  },
  projects: [
    { name: "desktop", use: { ...devices["Desktop Chrome"] } },
    { name: "mobile", use: { ...devices["Pixel 7"] } },
  ],
});
