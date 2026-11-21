import path from "node:path";
import { fileURLToPath } from "node:url";

import { defineConfig, devices } from "@playwright/test";

const webRoot = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(webRoot, "..", "..");
const host = "127.0.0.1";
const webPort = process.env.SMART_ENGINEER_WEB_PORT ?? "3000";
const apiPort = process.env.SMART_ENGINEER_API_PORT ?? "8000";
const baseURL = `http://${host}:${webPort}`;

// Full-stack run: the real Next.js server, the real FastAPI service and a real
// database. Nothing is mocked. The database must already be migrated and
// SMART_ENGINEER_DATABASE_URL must point at a disposable database (CI sets it).
export default defineConfig({
  testDir: path.join(webRoot, "e2e-fullstack"),
  fullyParallel: false,
  workers: 1,
  forbidOnly: Boolean(process.env.CI),
  retries: 0,
  reporter: [["list"]],
  outputDir: path.join(webRoot, "test-results-fullstack"),
  timeout: 60_000,
  use: { baseURL, locale: "fa-IR", trace: "retain-on-failure" },
  webServer: [
    {
      command: `uv run --package smart-engineer-api --group dev uvicorn --app-dir apps/api --host ${host} --port ${apiPort} smart_engineer_api.main:app`,
      cwd: repoRoot,
      url: `http://${host}:${apiPort}/health`,
      reuseExistingServer: false,
      timeout: 120_000,
      env: {
        ...process.env,
        SMART_ENGINEER_ENV: "development",
        // The browser's origin differs from the API host seen behind the proxy.
        SMART_ENGINEER_ALLOWED_ORIGINS: baseURL,
      },
    },
    {
      command: `node ./node_modules/next/dist/bin/next start --hostname ${host} --port ${webPort}`,
      cwd: webRoot,
      url: baseURL,
      reuseExistingServer: false,
      timeout: 60_000,
    },
  ],
  projects: [{ name: "desktop", use: { ...devices["Desktop Chrome"] } }],
});
