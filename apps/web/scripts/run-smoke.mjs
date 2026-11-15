// Starts the already-built production server, waits until it answers, runs the
// HTTP smoke tests against it, and always stops the server afterwards.
// Cross-platform (no shell, no bash-only syntax). Run `next build` first.
import { spawn } from "node:child_process";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";
import path from "node:path";

const require = createRequire(import.meta.url);
const webRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const host = "127.0.0.1";
const port = process.env.SMART_ENGINEER_WEB_PORT ?? "3000";
const baseUrl = `http://${host}:${port}`;
const startupTimeoutMs = 60_000;

const nextBin = require.resolve("next/dist/bin/next", { paths: [webRoot] });

const server = spawn(
  process.execPath,
  [nextBin, "start", "--hostname", host, "--port", port],
  { cwd: webRoot, stdio: ["ignore", "inherit", "inherit"] },
);

let serverExited = false;
server.on("exit", () => {
  serverExited = true;
});

function stopServer() {
  if (!serverExited) {
    server.kill();
  }
}

async function waitForServer() {
  const deadline = Date.now() + startupTimeoutMs;
  while (Date.now() < deadline) {
    if (serverExited) {
      throw new Error("The web server exited before it became ready.");
    }
    try {
      const response = await fetch(baseUrl);
      if (response.status === 200) {
        return;
      }
    } catch {
      // Not accepting connections yet; retry.
    }
    await new Promise((resolve) => setTimeout(resolve, 500));
  }
  throw new Error(`The web server did not become ready within ${startupTimeoutMs / 1000}s at ${baseUrl}.`);
}

let exitCode = 1;
try {
  await waitForServer();
  exitCode = await new Promise((resolve, reject) => {
    const tests = spawn(
      process.execPath,
      ["--test", path.join("tests", "smoke.test.mjs")],
      {
        cwd: webRoot,
        env: { ...process.env, SMART_ENGINEER_WEB_URL: baseUrl },
        stdio: "inherit",
      },
    );
    tests.on("error", reject);
    tests.on("exit", (code) => resolve(code ?? 1));
  });
} catch (error) {
  console.error(error instanceof Error ? error.message : error);
} finally {
  stopServer();
}

process.exit(exitCode);
