import { execFileSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { expect, test } from "@playwright/test";

// Real browser -> real API -> real database. The first administrator can only be made
// from the command line; everything after that goes through the audited admin API.
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

test("a bootstrapped administrator manages users and sees the audit trail", async ({
  page,
  browser,
}) => {
  const adminEmail = `root-${run}@example.com`;
  const memberEmail = `member-${run}@example.com`;

  await register(page, "مدیر آزمایشی", adminEmail);
  await expect(page.getByRole("link", { name: "مدیریت سیستم" })).toHaveCount(0);

  const memberContext = await browser.newContext();
  const memberPage = await memberContext.newPage();
  await register(memberPage, "کاربر عادی", memberEmail);
  await memberPage.goto("/admin");
  await expect(memberPage.getByRole("heading", { level: 1 })).toHaveText("صفحه پیدا نشد");

  execFileSync(
    "uv",
    [
      "run", "--package", "smart-engineer-api", "--group", "dev",
      "python", "-m", "smart_engineer_api.manage", "grant-admin", adminEmail,
    ],
    { cwd: repoRoot, env: process.env, stdio: "pipe" },
  );

  await page.reload();
  await page.getByRole("link", { name: "مدیریت سیستم" }).click();
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("مدیریت سیستم");

  await page.getByLabel("جست‌وجوی کاربر").fill(memberEmail);
  await page.getByRole("button", { name: "جست‌وجو" }).click();
  await page.getByRole("button", { name: "غیرفعال‌سازی کاربر عادی" }).click();
  await expect(page.getByRole("button", { name: "فعال‌سازی کاربر عادی" })).toBeVisible();

  // A deactivated account is locked out at once.
  await memberPage.reload();
  await expect(memberPage).toHaveURL(/\/login/);

  await page.getByRole("button", { name: "ممیزی" }).click();
  await expect(page.getByText("حساب کاربر غیرفعال شد")).toBeVisible();
  await expect(page.getByText("دسترسی مدیر سیستم داده شد")).toBeVisible();
  await memberContext.close();
});
