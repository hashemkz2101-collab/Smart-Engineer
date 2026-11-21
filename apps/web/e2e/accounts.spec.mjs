import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

import { error, mockApi, OWNER_PERMISSIONS, PROJECT } from "./api-mock.mjs";

const WCAG_TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"];

test.describe("sign-up and sign-in", () => {
  test("registering creates the account, signs in and lands on the project list", async ({
    page,
  }) => {
    const state = {};
    await mockApi(page, state);
    await page.goto("/register");

    await page.getByLabel("نام و نام خانوادگی").fill("علی رضایی");
    await page.getByLabel("ایمیل").fill("ali@example.com");
    await page.getByLabel("رمز عبور").fill("a long passphrase");
    await page.getByRole("button", { name: "ایجاد حساب" }).click();

    await expect(page).toHaveURL(/\/projects$/);
    await expect(page.getByRole("heading", { level: 1 })).toHaveText("پروژه‌ها");
    await expect(page.getByRole("banner").getByText("علی رضایی")).toBeVisible();
    const register = state.requests.find((r) => r.key === "POST /auth/register");
    expect(register.body).toEqual({
      email: "ali@example.com",
      display_name: "علی رضایی",
      password: "a long passphrase",
    });
  });

  test("a wrong password shows a Persian message and keeps the user on the page", async ({
    page,
  }) => {
    await mockApi(page, {}, {
      "POST /auth/login": (route) =>
        route.fulfill({
          status: 401,
          contentType: "application/json",
          body: JSON.stringify(error("invalid_credentials")),
        }).then(() => true),
    });
    await page.goto("/login");
    await page.getByLabel("ایمیل").fill("ali@example.com");
    await page.getByLabel("رمز عبور").fill("wrong password");
    await page.getByRole("button", { name: "ورود", exact: true }).click();

    await expect(page.locator("#main-content").getByRole("alert")).toHaveText("ایمیل یا رمز عبور درست نیست.");
    await expect(page).toHaveURL(/\/login$/);
  });

  test("a locked account explains the situation", async ({ page }) => {
    await mockApi(page, {}, {
      "POST /auth/login": (route) =>
        route.fulfill({
          status: 429,
          contentType: "application/json",
          body: JSON.stringify(error("account_locked")),
        }).then(() => true),
    });
    await page.goto("/login");
    await page.getByLabel("ایمیل").fill("ali@example.com");
    await page.getByLabel("رمز عبور").fill("whatever it is");
    await page.getByRole("button", { name: "ورود", exact: true }).click();

    await expect(page.locator("#main-content").getByRole("alert")).toContainText("تلاش‌های ناموفق زیاد بود");
  });

  test("protected pages send anonymous visitors to the login page and back", async ({ page }) => {
    await mockApi(page, {});
    await page.goto("/projects");

    await expect(page).toHaveURL(/\/login\?next=%2Fprojects$/);
    await page.getByLabel("ایمیل").fill("ali@example.com");
    await page.getByLabel("رمز عبور").fill("a long passphrase");
    await page.getByRole("button", { name: "ورود", exact: true }).click();
    await expect(page).toHaveURL(/\/projects$/);
  });

  test("the next parameter cannot redirect to another site", async ({ page }) => {
    await mockApi(page, {});
    await page.goto("/login?next=//evil.example/steal");
    await page.getByLabel("ایمیل").fill("ali@example.com");
    await page.getByLabel("رمز عبور").fill("a long passphrase");
    await page.getByRole("button", { name: "ورود", exact: true }).click();

    await expect(page).toHaveURL(/127\.0\.0\.1.*\/projects$/);
  });

  test("password recovery always shows the same neutral message", async ({ page }) => {
    await mockApi(page, {});
    await page.goto("/forgot-password");
    await page.getByLabel("ایمیل").fill("nobody@example.com");
    await page.getByRole("button", { name: "درخواست پیوند بازیابی" }).click();

    await expect(page.getByRole("status")).toContainText("اگر حسابی با این ایمیل وجود داشته باشد");
  });

  test("signing out clears the session and the header offers sign-in again", async ({ page }) => {
    const state = { loggedIn: true };
    await mockApi(page, state);
    await page.goto("/projects");
    await page.getByRole("button", { name: "خروج" }).click();

    await expect(page.getByRole("link", { name: "ورود", exact: true })).toBeVisible();
    const logout = state.requests.find((r) => r.key === "POST /auth/logout");
    expect(logout.headers["x-csrf-token"]).toBe("csrf-1");
  });
});

test.describe("projects", () => {
  test("creating a project sends the CSRF token and opens the new project", async ({ page }) => {
    const state = { loggedIn: true };
    await mockApi(page, state);
    await page.goto("/projects");

    await page.getByLabel("نام پروژه").fill("ویلای نمونه");
    await page.getByLabel("نوع پروژه").selectOption("residential_house");
    await page.getByRole("button", { name: "ایجاد پروژه" }).click();

    await expect(page).toHaveURL(new RegExp(`/projects/${PROJECT.id}$`));
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(PROJECT.name);
    const create = state.requests.find((r) => r.key === "POST /projects");
    expect(create.headers["x-csrf-token"]).toBe("csrf-1");
    expect(create.body).toMatchObject({
      organization_id: "o-1",
      name: "ویلای نمونه",
      project_type: "residential_house",
    });
  });

  test("the archived tab asks the API for archived projects only", async ({ page }) => {
    const state = { loggedIn: true };
    await mockApi(page, state);
    await page.goto("/projects");
    await page.getByRole("button", { name: "بایگانی‌شده" }).click();

    await expect(page.getByText("پروژهٔ بایگانی‌شده‌ای وجود ندارد.")).toBeVisible();
    expect(state.requests.some((r) => r.query.includes("archived=true"))).toBe(true);
  });

  test("controls follow the permissions the API reports", async ({ page }) => {
    const state = { loggedIn: true, permissions: ["project.view"] };
    await mockApi(page, state);
    await page.goto(`/projects/${PROJECT.id}`);

    await expect(page.getByRole("heading", { level: 1 })).toHaveText(PROJECT.name);
    await expect(page.getByRole("button", { name: "بایگانی پروژه" })).toHaveCount(0);
    await expect(page.getByRole("button", { name: "ذخیرهٔ تغییرات" })).toHaveCount(0);
    await expect(page.getByText("تاریخچهٔ فعالیت")).toBeVisible();
  });

  test("an archived project shows a read-only notice and a restore button", async ({ page }) => {
    const state = {
      loggedIn: true,
      project: { ...PROJECT, status: "archived", archived_at: "2026-11-21T10:00:00+00:00" },
      permissions: ["project.view", "project.restore"],
    };
    await mockApi(page, state);
    await page.goto(`/projects/${PROJECT.id}`);

    await expect(page.getByText("این پروژه بایگانی شده و فقط‌خواندنی است.")).toBeVisible();
    await expect(page.getByRole("button", { name: "بازگردانی از بایگانی" })).toBeVisible();
    await expect(page.getByRole("button", { name: "ذخیرهٔ تغییرات" })).toHaveCount(0);
  });

  test("a project the caller cannot see shows a not-found message", async ({ page }) => {
    await mockApi(page, { loggedIn: true }, {
      [`GET /projects/${PROJECT.id}`]: (route) =>
        route.fulfill({
          status: 404,
          contentType: "application/json",
          body: JSON.stringify(error("http_404")),
        }).then(() => true),
    });
    await page.goto(`/projects/${PROJECT.id}`);

    await expect(page.locator("#main-content").getByRole("alert")).toHaveText("مورد درخواستی پیدا نشد.");
  });
});

test.describe("accessibility and layout of the new pages", () => {
  const pages = [
    ["login", "/login", false],
    ["register", "/register", false],
    ["forgot-password", "/forgot-password", false],
    ["reset-password", "/reset-password?token=abc", false],
    ["projects", "/projects", true],
    ["project detail", `/projects/${PROJECT.id}`, true],
    ["organization", "/organization", true],
    ["accept invitation", "/invitations/accept?token=abc", true],
  ];

  for (const [name, path, loggedIn] of pages) {
    for (const scheme of ["light", "dark"]) {
      test(`${name} has no axe WCAG A/AA violations (${scheme})`, async ({ page }) => {
        await mockApi(page, { loggedIn, permissions: OWNER_PERMISSIONS });
        await page.emulateMedia({ colorScheme: scheme });
        await page.goto(path);
        await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
        await expect(page.getByText("در حال بارگذاری…")).toHaveCount(0);

        const results = await new AxeBuilder({ page }).withTags(WCAG_TAGS).analyze();

        expect(
          results.violations.map((v) => ({
            id: v.id,
            targets: v.nodes.map((node) => node.target.join(" ")),
          })),
        ).toEqual([]);
      });
    }

    test(`${name} has no horizontal overflow at 320px`, async ({ page }) => {
      await mockApi(page, { loggedIn, permissions: OWNER_PERMISSIONS });
      await page.setViewportSize({ width: 320, height: 800 });
      await page.goto(path);
      await expect(page.getByRole("heading", { level: 1 })).toBeVisible();

      const overflow = await page.evaluate(
        () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
      );
      expect(overflow).toBeLessThanOrEqual(0);
    });
  }
});
