import { execFileSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { expect, test } from "@playwright/test";

// TEMPORARY diagnosis of an intermittent missing redirect to /login. Not for merging.
const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../../..");
const run = Date.now().toString(36);
const PASSWORD = "a long passphrase 1";

async function register(page, name, email) {
  await page.goto("/register");
  await page.getByLabel("نام و نام خانوادگی").fill(name);
  await page.getByLabel("ایمیل").fill(email);
  await page.getByLabel("رمز عبور").fill(PASSWORD);
  await page.getByRole("button", { name: "ایجاد حساب" }).click();
  await expect(page).toHaveURL(/\/projects$/);
}

test("diagnose redirect after deactivation", async ({ page, browser }) => {
  test.setTimeout(280_000);
  const adminEmail = `diag-root-${run}@example.com`;
  await register(page, "مدیر", adminEmail);
  execFileSync(
    "uv",
    ["run", "--package", "smart-engineer-api", "--group", "dev", "python", "-m",
      "smart_engineer_api.manage", "grant-admin", adminEmail],
    { cwd: repoRoot, env: { ...process.env, PYTHONPATH: path.join(repoRoot, "apps/api") }, stdio: "pipe" },
  );
  await page.reload();
  const me = await (await page.request.get("/api/v1/auth/me")).json();
  const csrf = me.csrf_token;

  const failures = [];
  for (let i = 0; i < 12; i += 1) {
    const email = `diag-m${i}-${run}@example.com`;
    const context = await browser.newContext();
    const member = await context.newPage();
    await register(member, "کاربر", email);
    await member.goto("/admin");
    await expect(member.getByRole("heading", { level: 1 })).toHaveText("صفحه پیدا نشد");

    const list = await (await page.request.get(`/api/v1/admin/users?q=${email}`)).json();
    const id = list.users[0].id;
    const put = await page.request.put(`/api/v1/admin/users/${id}/active`, {
      headers: { "X-CSRF-Token": csrf },
      data: { active: false },
    });
    expect(put.status()).toBe(200);

    const log = [];
    const t0 = Date.now();
    const stamp = (text) => log.push(`${Date.now() - t0}ms ${text}`);
    member.on("request", (r) => stamp(`REQ ${r.method()} ${new URL(r.url()).pathname}`));
    member.on("response", (r) => stamp(`RES ${r.status()} ${new URL(r.url()).pathname}`));
    member.on("requestfailed", (r) => stamp(`FAIL ${new URL(r.url()).pathname} ${r.failure()?.errorText}`));
    member.on("console", (m) => stamp(`CONSOLE ${m.type()} ${m.text().slice(0, 200)}`));
    member.on("pageerror", (e) => stamp(`PAGEERROR ${String(e).slice(0, 200)}`));
    member.on("framenavigated", (f) => f === member.mainFrame() && stamp(`NAV ${new URL(f.url()).pathname}`));

    await member.goto("/admin");
    stamp(`goto returned; visibility=${await member.evaluate(() => document.visibilityState)}`);
    let redirected = true;
    try {
      await expect(member).toHaveURL(/\/login/, { timeout: 8000 });
    } catch {
      redirected = false;
    }
    stamp(`body=${(await member.locator("body").innerText()).replace(/\s+/g, " ").slice(0, 120)}`);
    console.log(`DIAG iteration ${i}: redirected=${redirected}\n  ${log.join("\n  ")}`);
    if (!redirected) failures.push(i);
    await context.close();
  }
  console.log(`DIAG failures: ${JSON.stringify(failures)}`);
});
