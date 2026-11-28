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

test.describe("project intake", () => {
  const intakeUrl = `/projects/${PROJECT.id}`;

  test("a step can be saved incomplete and tells what is still missing", async ({ page }) => {
    const state = { loggedIn: true };
    await mockApi(page, state, {
      [`PUT /projects/${PROJECT.id}/intake/location`]: (route) =>
        route
          .fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify({
              step: "location",
              data: { city: "تهران" },
              complete: false,
              missing: ["province"],
              version: 1,
            }),
          })
          .then(() => true),
    });
    await page.goto(intakeUrl);
    await page.getByRole("button", { name: /موقعیت/ }).click();
    await page.getByLabel("شهر (ضروری)").fill("تهران");
    await page.getByRole("button", { name: "ذخیرهٔ این مرحله" }).click();

    await expect(page.getByRole("status").filter({ hasText: "ذخیره شد." })).toContainText("استان");
    const put = state.requests.find((r) => r.key.startsWith("PUT") && r.key.endsWith("/location"));
    expect(put.headers["x-csrf-token"]).toBe("csrf-1");
    expect(put.body.version).toBe(0);
    expect(put.body.data.city).toBe("تهران");
  });

  test("edits typed while the step list reloads after a save are kept", async ({ page }) => {
    const state = { loggedIn: true, intake: {} };
    const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
    await mockApi(page, state, {
      [`PUT /projects/${PROJECT.id}/intake/location`]: (route) => {
        state.intake.location = { data: { city: "تهران" }, complete: false, version: 1 };
        return route
          .fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify({
              step: "location",
              data: { city: "تهران" },
              complete: false,
              missing: ["province"],
              version: 1,
            }),
          })
          .then(() => true);
      },
      // The refetch after a save arrives late, as it can on a slow network.
      [`GET /projects/${PROJECT.id}/intake`]: async (route) => {
        if (state.intake.location) await sleep(1200);
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            steps: ["identity", "location", "people", "legal"].map((step) => ({
              step,
              data: state.intake[step]?.data ?? {},
              complete: state.intake[step]?.complete ?? false,
              missing: [],
              version: state.intake[step]?.version ?? 0,
              updated_at: null,
            })),
          }),
        });
        return true;
      },
    });
    await page.goto(intakeUrl);
    await page.getByRole("button", { name: /موقعیت/ }).click();
    await page.getByLabel("شهر (ضروری)").fill("تهران");
    await page.getByRole("button", { name: "ذخیرهٔ این مرحله" }).click();
    await expect(page.getByRole("status").filter({ hasText: "ذخیره شد." })).toBeVisible();

    await page.getByLabel("استان (ضروری)").fill("تهران");
    await page.waitForTimeout(2000); // let the late refetch land
    await expect(page.getByLabel("استان (ضروری)")).toHaveValue("تهران");
    await expect(page.getByLabel("شهر (ضروری)")).toHaveValue("تهران");
  });

  test("field errors from the API are shown next to the fields", async ({ page }) => {
    await mockApi(page, { loggedIn: true }, {
      [`PUT /projects/${PROJECT.id}/intake/location`]: (route) =>
        route
          .fulfill({
            status: 422,
            contentType: "application/json",
            body: JSON.stringify({
              error: {
                code: "invalid_intake",
                message: "x",
                correlation_id: "t",
                details: [{ field: "latitude", reason: "out_of_range" }],
              },
            }),
          })
          .then(() => true),
    });
    await page.goto(intakeUrl);
    await page.getByRole("button", { name: /موقعیت/ }).click();
    await page.getByLabel("عرض جغرافیایی").fill("95");
    await page.getByRole("button", { name: "ذخیرهٔ این مرحله" }).click();

    await expect(page.getByText("عدد خارج از محدودهٔ مجاز است.")).toBeVisible();
    await expect(page.getByLabel("عرض جغرافیایی")).toHaveAttribute("aria-invalid", "true");
  });

  test("members without edit permission see the data read-only", async ({ page }) => {
    await mockApi(page, {
      loggedIn: true,
      permissions: ["project.view"],
      intake: { people: { data: { client: "شرکت نمونه" }, complete: true, version: 1 } },
    });
    await page.goto(intakeUrl);
    await page.getByRole("button", { name: /افراد/ }).click();

    await expect(page.getByLabel("کارفرما (ضروری)")).toHaveValue("شرکت نمونه");
    await expect(page.getByLabel("کارفرما (ضروری)")).toBeDisabled();
    await expect(page.getByRole("button", { name: "ذخیرهٔ این مرحله" })).toHaveCount(0);
  });
});

test.describe("site data", () => {
  const url = `/projects/${PROJECT.id}`;
  const parcelResponse = {
    section: "parcel",
    data: { shape: "irregular" },
    complete: true,
    missing: [],
    not_provided: [],
    version: 1,
    derived: {
      status: "discrepancy",
      area_source: "vertices",
      computed_area_m2: 75,
      declared_area_m2: 80,
      difference_m2: -5,
      difference_percent: 6.25,
      tolerance_percent: 1,
      computed_side_lengths_m: [10, 5, 5, 5, 5, 10],
    },
  };

  test("an irregular parcel is sent as vertices and the area discrepancy is shown", async ({ page }) => {
    const state = { loggedIn: true };
    await mockApi(page, state, {
      [`PUT /projects/${PROJECT.id}/site/parcel`]: (route) =>
        route
          .fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(parcelResponse) })
          .then(() => true),
    });
    await page.goto(url);
    await page.getByLabel("شکل قطعه").selectOption("irregular");
    await page.getByLabel("مساحت اظهارشده (متر مربع)").fill("80");
    for (const [index, [x, y]] of [["0", "0"], ["10", "0"], ["10", "5"]].entries()) {
      await page.getByRole("button", { name: "افزودن ردیف به رئوس مرز (به ترتیب دور قطعه)" }).click();
      await page.getByLabel(`رئوس مرز (به ترتیب دور قطعه) ${index + 1}: X (ضروری)`).fill(x);
      await page.getByLabel(`رئوس مرز (به ترتیب دور قطعه) ${index + 1}: Y (ضروری)`).fill(y);
    }
    await page.getByRole("button", { name: "ذخیرهٔ این بخش" }).click();

    await expect(page.getByRole("status").filter({ hasText: "ذخیره شد؛ این بخش کامل است." })).toBeVisible();
    const put = state.requests.find((r) => r.key === `PUT /projects/${PROJECT.id}/site/parcel`);
    expect(put.headers["x-csrf-token"]).toBe("csrf-1");
    expect(put.body.version).toBe(0);
    expect(put.body.data.vertices).toEqual([
      { x: "0", y: "0" },
      { x: "10", y: "0" },
      { x: "10", y: "5" },
    ]);
    expect(put.body.data.sides).toBeUndefined();
  });

  test("the API's computed area report is displayed with the discrepancy", async ({ page }) => {
    await mockApi(page, { loggedIn: true, site: { parcel: parcelResponse } });
    await page.goto(url);
    const report = page.getByTestId("area-report");
    await expect(report).toHaveAttribute("data-status", "discrepancy");
    await expect(report).toContainText("اختلاف مساحت");
    await expect(report).toContainText("75");
    await expect(report).toContainText("80");
    await expect(report).toContainText("این اختلاف باید بررسی شود");
  });

  test("list errors from the API name the row and column", async ({ page }) => {
    await mockApi(page, { loggedIn: true }, {
      [`PUT /projects/${PROJECT.id}/site/parcel`]: (route) =>
        route
          .fulfill({
            status: 422,
            contentType: "application/json",
            body: JSON.stringify({
              error: {
                code: "invalid_site",
                message: "x",
                correlation_id: "t",
                details: [{ field: "vertices", reason: "too_few_points" }],
              },
            }),
          })
          .then(() => true),
    });
    await page.goto(url);
    await page.getByLabel("شکل قطعه").selectOption("polygon");
    await page.getByRole("button", { name: "ذخیرهٔ این بخش" }).click();
    await expect(page.getByText("دست‌کم سه نقطه لازم است.")).toBeVisible();
  });

  test("omitted soil values are reported as not provided and surroundings send explicit lists", async ({ page }) => {
    const state = { loggedIn: true, site: { soil: { data: { soil_type: "clay" }, complete: true, version: 1,
      not_provided: ["bearing_capacity_kpa", "groundwater_depth_m", "report_reference"] } } };
    await mockApi(page, state, {
      [`PUT /projects/${PROJECT.id}/site/surroundings`]: (route) =>
        route
          .fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify({ section: "surroundings", data: {}, complete: true, missing: [],
              not_provided: [], version: 1 }),
          })
          .then(() => true),
    });
    await page.goto(url);
    await page.getByRole("button", { name: /خاک/ }).click();
    const missing = page.getByTestId("soil-not-provided");
    await expect(missing).toContainText("ثبت‌نشده");
    await expect(missing).toContainText("ظرفیت باربری");
    await expect(page.getByLabel("ظرفیت باربری (کیلوپاسکال)")).toHaveValue("");

    await page.getByRole("button", { name: /محیط اطراف/ }).click();
    await page.getByRole("button", { name: "افزودن ردیف به همسایگان" }).click();
    await page.getByLabel("همسایگان 1: سمت (ضروری)").selectOption("east");
    await page.getByLabel("دیوار مشترک").check();
    await page.getByRole("button", { name: "ذخیرهٔ این بخش" }).click();
    await expect(page.getByRole("status").filter({ hasText: "ذخیره شد" })).toBeVisible();
    const put = state.requests.find((r) => r.key.endsWith("/site/surroundings"));
    expect(put.body.data.neighbors).toEqual([{ side: "east", shared_wall: true }]);
    for (const name of ["trees", "wells", "channels", "existing_utilities", "easements"]) {
      expect(put.body.data[name]).toEqual([]);
    }
  });

  test("members without edit permission see site data read-only", async ({ page }) => {
    await mockApi(page, {
      loggedIn: true,
      permissions: ["project.view"],
      site: { soil: { data: { soil_type: "rock" }, complete: true, version: 1, not_provided: [] } },
    });
    await page.goto(url);
    await page.getByRole("button", { name: /خاک/ }).click();
    await expect(page.getByLabel("نوع خاک")).toHaveValue("rock");
    await expect(page.getByLabel("نوع خاک")).toBeDisabled();
    await expect(page.getByRole("button", { name: "ذخیرهٔ این بخش" })).toHaveCount(0);
  });
});

test.describe("zoning inputs", () => {
  const url = `/projects/${PROJECT.id}`;

  test("an unsourced value is saved and shown as needing inquiry", async ({ page }) => {
    const state = { loggedIn: true };
    await mockApi(page, state, {
      [`PUT /projects/${PROJECT.id}/zoning/coverage`]: (route) =>
        route
          .fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify({
              field: "coverage",
              data: { max_coverage_percent: 60 },
              status: "needs_inquiry",
              source_missing: ["source_type", "source_date", "source_title_or_reference"],
              version: 1,
            }),
          })
          .then(() => true),
    });
    await page.goto(url);
    await page.getByRole("button", { name: /سطح اشغال/ }).click();
    await expect(page.getByTestId("zoning-status")).toHaveAttribute("data-status", "unknown");
    await page.getByLabel("حداکثر سطح اشغال (درصد)").fill("60");
    await page.getByRole("button", { name: "ذخیرهٔ این ضابطه" }).click();

    await expect(page.getByRole("status").filter({ hasText: "ذخیره شد؛ وضعیت: نیازمند استعلام." })).toBeVisible();
    const put = state.requests.find((r) => r.key === `PUT /projects/${PROJECT.id}/zoning/coverage`);
    expect(put.headers["x-csrf-token"]).toBe("csrf-1");
    expect(put.body).toEqual({ data: { max_coverage_percent: "60" }, version: 0 });
  });

  test("the source fields and verification are sent with the value", async ({ page }) => {
    const state = { loggedIn: true };
    await mockApi(page, state, {
      [`PUT /projects/${PROJECT.id}/zoning/coverage`]: (route) =>
        route
          .fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify({ field: "coverage", data: {}, status: "verified",
              source_missing: [], version: 1 }),
          })
          .then(() => true),
    });
    await page.goto(url);
    await page.getByRole("button", { name: /سطح اشغال/ }).click();
    await page.getByLabel("حداکثر سطح اشغال (درصد)").fill("60");
    await page.getByLabel("نوع منبع").selectOption("municipality_letter");
    await page.getByLabel("عنوان منبع").fill("نامهٔ شهرداری");
    await page.getByLabel("تاریخ منبع").fill("1405-02-10");
    await page.getByLabel("تقویم تاریخ").selectOption("jalali");
    await page.getByLabel(/تأیید می‌کنم/).check();
    await page.getByRole("button", { name: "ذخیرهٔ این ضابطه" }).click();
    await expect(page.getByRole("status").filter({ hasText: "تأییدشده" })).toBeVisible();
    const put = state.requests.find((r) => r.key.endsWith("/zoning/coverage"));
    expect(put.body.data).toEqual({
      max_coverage_percent: "60",
      source_type: "municipality_letter",
      source_title: "نامهٔ شهرداری",
      source_date: "1405-02-10",
      source_calendar: "jalali",
      source_verified: true,
    });
  });

  test("API field errors are shown next to the fields", async ({ page }) => {
    await mockApi(page, { loggedIn: true }, {
      [`PUT /projects/${PROJECT.id}/zoning/coverage`]: (route) =>
        route
          .fulfill({
            status: 422,
            contentType: "application/json",
            body: JSON.stringify({ error: { code: "invalid_zoning", message: "x", correlation_id: "t",
              details: [{ field: "source_calendar", reason: "calendar_required" }] } }),
          })
          .then(() => true),
    });
    await page.goto(url);
    await page.getByRole("button", { name: /سطح اشغال/ }).click();
    await page.getByLabel("تاریخ منبع").fill("1405-02-10");
    await page.getByRole("button", { name: "ذخیرهٔ این ضابطه" }).click();
    await expect(page.getByText("با تاریخ، تقویم آن را هم انتخاب کنید.")).toBeVisible();
    await expect(page.getByLabel("تقویم تاریخ")).toHaveAttribute("aria-invalid", "true");
  });

  test("stored status and missing source parts are displayed; view-only members cannot edit", async ({ page }) => {
    await mockApi(page, {
      loggedIn: true,
      permissions: ["project.view"],
      zoning: { coverage: { data: { max_coverage_percent: 60 }, status: "needs_inquiry",
        source_missing: ["source_date"], version: 1 } },
    });
    await page.goto(url);
    await page.getByRole("button", { name: /سطح اشغال/ }).click();
    const status = page.getByTestId("zoning-status");
    await expect(status).toHaveAttribute("data-status", "needs_inquiry");
    await expect(status).toContainText("تاریخ منبع");
    await expect(page.getByLabel("حداکثر سطح اشغال (درصد)")).toBeDisabled();
    await expect(page.getByRole("button", { name: "ذخیرهٔ این ضابطه" })).toHaveCount(0);
  });
});

test.describe("space schedule", () => {
  const url = `/projects/${PROJECT.id}`;
  const schedule = {
    exists: true,
    version: 1,
    stale: true,
    program_version: 3,
    program_ready: true,
    updated_at: null,
    data: {
      source: { program_version: 2, units_count: 1, floors_count: 1 },
      counts_basis: "as_listed",
      spaces: [
        { id: "S-001", kind: "bedroom", room_index: 0, ordinal: 1, of: 2, target_area_m2: 14 },
        { id: "S-002", kind: "bedroom", room_index: 0, ordinal: 2, of: 2, target_area_m2: 14 },
        { id: "S-003", kind: "yard", room_index: 1, ordinal: 1, of: 1 },
      ],
      totals: { rooms: 2, spaces: 3, spaces_with_area: 2, spaces_without_area: 1,
        area_lower_m2: 28, area_upper_m2: 28, target_sum_m2: 28, bounds_complete: false },
      flags: [{ code: "area_not_given", severity: "warning", room_index: 1 }],
      limitations: ["net_room_areas_only"],
    },
  };

  test("saved schedule shows totals, flags, stale warning and limits", async ({ page }) => {
    await mockApi(page, { loggedIn: true, spaceSchedule: schedule });
    await page.goto(url);
    await expect(page.getByTestId("schedule-totals")).toContainText("ناقص");
    await expect(page.getByRole("row")).toHaveCount(4);
    await expect(page.getByText("برای این ردیف هیچ مساحتی وارد نشده است.")).toBeVisible();
    await expect(page.getByText("فهرست قدیمی است")).toBeVisible();
    await expect(page.getByText("دیوار، راهرو و سازه شامل نیست.")).toBeVisible();
  });

  test("generating sends the current schedule version; viewers cannot generate", async ({ page }) => {
    const state = { loggedIn: true, spaceSchedule: { ...schedule, stale: false } };
    await mockApi(page, state, {
      [`POST /projects/${PROJECT.id}/space-schedule/generate`]: (route) =>
        route
          .fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(schedule) })
          .then(() => true),
    });
    await page.goto(url);
    await page.getByRole("button", { name: "ساخت دوبارهٔ فهرست" }).click();
    await expect(page.getByRole("status").filter({ hasText: "ساخته و ذخیره شد" })).toBeVisible();
    const post = state.requests.find((r) => r.key.endsWith("/space-schedule/generate"));
    expect(post.headers["x-csrf-token"]).toBe("csrf-1");
    expect(post.body).toEqual({ version: 1 });
  });

  test("view-only members see the schedule without a generate button", async ({ page }) => {
    await mockApi(page, { loggedIn: true, permissions: ["project.view"], spaceSchedule: schedule });
    await page.goto(url);
    await expect(page.getByTestId("schedule-totals")).toBeVisible();
    await expect(page.getByRole("button", { name: /ساخت/ })).toHaveCount(0);
  });
});

test.describe("conceptual layouts", () => {
  const url = `/projects/${PROJECT.id}`;
  const alternative = (id, strategy) => ({
    id, strategy,
    criteria: ["largest_spaces_first", "compact_from_the_lower_left_corner"],
    assumptions: [],
    not_evaluated: ["regulation_compliance", "orientation_and_daylight"],
    limitations: ["conceptual_blocks_not_a_plan"],
    floors: [
      { floor: 1, used_area_m2: 40, placements: [
        { space_id: "S-001", kind: "living", x: 0, y: 0, width: 5, height: 4, area_m2: 20, area_basis: "target" },
        { space_id: "S-002", kind: "bedroom", x: 5, y: 0, width: 5, height: 4, area_m2: 20, area_basis: "range_midpoint" },
      ] },
      { floor: 2, used_area_m2: 12, placements: [
        { space_id: "S-003", kind: "kitchen", x: 0, y: 0, width: 4, height: 3, area_m2: 12, area_basis: "target" },
      ] },
    ],
    unplaced: [{ space_id: "S-004", kind: "yard", reason: "outdoor_space_not_modelled" }],
    metrics: { placed_spaces: 3, unplaced_spaces: 1, placed_area_m2: 52, fully_placed: true, floors_used: 2 },
  });
  const layouts = {
    exists: true, version: 1, stale: false, updated_at: null,
    data: {
      status: "alternatives", reasons: [], details: {},
      envelope_polygons: [{ exterior: [[0, 0], [16, 0], [16, 10], [0, 10]], holes: [] }],
      alternatives: [alternative("ALT-1", "privacy_bands"), alternative("ALT-2", "largest_first_compact")],
    },
  };

  test("alternatives show strategy, blocks, unplaced spaces, criteria and what was not evaluated", async ({ page }) => {
    await mockApi(page, { loggedIn: true, layouts });
    await page.goto(url);
    await expect(page.getByTestId("layout-strategy")).toContainText("پهنه‌بندی خصوصی‌بودن");
    await expect(page.getByRole("img", { name: /طبقهٔ 1 در گزینهٔ ALT-1/ })).toBeVisible();
    await expect(page.getByText("میانهٔ بازه")).toBeVisible();
    await expect(page.getByText("فضای باز؛ در این مرحله مدل نمی‌شود")).toBeVisible();
    await expect(page.getByRole("list", { name: "بررسی‌نشده" }).getByText("انطباق با ضوابط")).toBeVisible();
    await page.getByRole("button", { name: "ALT-2" }).click();
    await expect(page.getByTestId("layout-strategy")).toContainText("پایین‌چپ");
    await page.getByRole("button", { name: /طبقهٔ ۲/ }).click();
    await expect(page.getByRole("cell", { name: "S-003" })).toBeVisible();
  });

  test("an infeasible result lists its specific reasons and a stale result is flagged", async ({ page }) => {
    await mockApi(page, {
      loggedIn: true,
      layouts: { exists: true, version: 2, stale: true, updated_at: null, data: {
        status: "infeasible", details: {}, alternatives: [],
        reasons: ["envelope_not_computed", "front_m_required"] } },
    });
    await page.goto(url);
    const box = page.getByTestId("layout-infeasible");
    await expect(box).toContainText("محدودهٔ قابل ساخت محاسبه نشد");
    await expect(box).toContainText("عقب‌نشینی جلو ثبت نشده است");
    await expect(page.getByText("نتیجه قدیمی است")).toBeVisible();
  });

  test("generating sends the stored version; viewers cannot generate", async ({ page }) => {
    const state = { loggedIn: true, layouts };
    await mockApi(page, state, {
      [`POST /projects/${PROJECT.id}/layouts/generate`]: (route) =>
        route
          .fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(layouts) })
          .then(() => true),
    });
    await page.goto(url);
    await page.getByRole("button", { name: "ساخت دوبارهٔ گزینه‌ها" }).click();
    await expect(page.getByRole("status").filter({ hasText: "ساخته و ذخیره شد" })).toBeVisible();
    const post = state.requests.find((r) => r.key.endsWith("/layouts/generate"));
    expect(post.headers["x-csrf-token"]).toBe("csrf-1");
    expect(post.body).toEqual({ version: 1 });
  });

  test("view-only members see the options without a generate button", async ({ page }) => {
    await mockApi(page, { loggedIn: true, permissions: ["project.view"], layouts });
    await page.goto(url);
    await expect(page.getByTestId("layout-strategy")).toBeVisible();
    await expect(page.getByRole("button", { name: /ساخت دوبارهٔ گزینه/ })).toHaveCount(0);
  });
});

test.describe("design editing", () => {
  const url = `/projects/${PROJECT.id}`;
  const design = {
    exists: true, version: 3, layout_changed: false, updated_at: null,
    data: {
      schema: 1, units: "m", next_id: 5,
      source: { kind: "layout", layout_version: 1, alternative_id: "ALT-1", strategy: "privacy_bands" },
      elements: [
        { id: "E-0001", type: "space", floor: 1, locked: false, kind: "living", x: 0, y: 0, width: 5, height: 4, rotation_deg: 0 },
        { id: "E-0002", type: "space", floor: 1, locked: true, kind: "bedroom", x: 5, y: 0, width: 4, height: 4, rotation_deg: 0 },
        { id: "E-0003", type: "wall", floor: 1, locked: false, x1: 0, y1: 0, x2: 9, y2: 0, thickness_m: 0.2 },
        { id: "E-0004", type: "door", floor: 1, locked: false, wall_id: "E-0003", offset_m: 1, width_m: 0.9 },
      ],
    },
  };
  const reply = (status, body) => (route) =>
    route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) }).then(() => true);

  test("elements are listed with lock state and an edit is sent with the stored version", async ({ page }) => {
    const state = { loggedIn: true, design };
    await mockApi(page, state, {
      [`POST /projects/${PROJECT.id}/design/edit`]: reply(200, { ...design, version: 4 }),
    });
    await page.goto(url);
    await expect(page.getByRole("img", { name: /نمای طرح/ })).toBeVisible();
    await expect(page.getByRole("cell", { name: /^E-0002 —/ })).toBeVisible();
    await expect(page.getByRole("cell", { name: "قفل", exact: true })).toBeVisible();
    await page.getByRole("button", { name: "انتخاب E-0001" }).click();
    await page.getByRole("button", { name: "قفل کردن" }).click();
    await expect(page.getByRole("status").filter({ hasText: "عنصر قفل شد" })).toBeVisible();
    const post = state.requests.find((r) => r.key.endsWith("/design/edit"));
    expect(post.headers["x-csrf-token"]).toBe("csrf-1");
    expect(post.body).toEqual({ version: 3, operations: [{ op: "lock", id: "E-0001" }] });
  });

  test("a locked element shows its explicit reason and can be unlocked", async ({ page }) => {
    await mockApi(page, { loggedIn: true, design }, {
      [`POST /projects/${PROJECT.id}/design/edit`]: reply(409, {
        error: { code: "element_locked", message: "locked", correlation_id: null,
          details: [{ operation_index: 0, element_id: "E-0002" }] } }),
    });
    await page.goto(url);
    await page.getByRole("button", { name: "انتخاب E-0002" }).click();
    await expect(page.getByRole("button", { name: "باز کردن قفل" })).toBeVisible();
    await page.getByRole("button", { name: "جابه‌جایی", exact: true }).click();
    await expect(page.getByRole("alert").filter({ hasText: "این عنصر قفل است" })).toBeVisible();
  });

  test("importing a layout option sends the chosen alternative; viewers have no edit controls", async ({ page }) => {
    const layouts = { exists: true, version: 1, stale: false, updated_at: null,
      data: { status: "alternatives", reasons: [], details: {}, alternatives: [
        { id: "ALT-1", strategy: "privacy_bands", criteria: [], assumptions: [], not_evaluated: [],
          limitations: [], floors: [], unplaced: [],
          metrics: { placed_spaces: 0, unplaced_spaces: 0, placed_area_m2: 0, fully_placed: true, floors_used: 0 } },
        { id: "ALT-2", strategy: "largest_first_compact", criteria: [], assumptions: [], not_evaluated: [],
          limitations: [], floors: [], unplaced: [],
          metrics: { placed_spaces: 0, unplaced_spaces: 0, placed_area_m2: 0, fully_placed: true, floors_used: 0 } },
      ] } };
    const state = { loggedIn: true, layouts };
    await mockApi(page, state, {
      [`POST /projects/${PROJECT.id}/design/import-layout`]: reply(200, design),
    });
    await page.goto(url);
    await page.locator("select").filter({ has: page.locator('option[value="ALT-2"]') }).selectOption("ALT-2");
    await page.getByRole("button", { name: "واردکردن گزینه به‌عنوان طرح" }).click();
    await expect(page.getByRole("status").filter({ hasText: "وارد شد" })).toBeVisible();
    const post = state.requests.find((r) => r.key.endsWith("/design/import-layout"));
    expect(post.body).toEqual({ alternative_id: "ALT-2", version: 0, replace: false });
  });

  test("view-only members see the design without edit or import controls", async ({ page }) => {
    await mockApi(page, { loggedIn: true, permissions: ["project.view"], design });
    await page.goto(url);
    await expect(page.getByRole("cell", { name: /^E-0001 —/ })).toBeVisible();
    await page.getByRole("button", { name: "انتخاب E-0001" }).click();
    await expect(page.getByRole("button", { name: "قفل کردن" })).toHaveCount(0);
    await expect(page.getByRole("button", { name: "واردکردن گزینه به‌عنوان طرح" })).toHaveCount(0);
  });
});

test.describe("client requirements", () => {
  const url = `/projects/${PROJECT.id}`;
  const ok = (body) => (route) =>
    route
      .fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(body) })
      .then(() => true);

  test("the space program is sent with counts and rooms", async ({ page }) => {
    const state = { loggedIn: true };
    await mockApi(page, state, {
      [`PUT /projects/${PROJECT.id}/requirements/program`]: ok({
        section: "program", data: {}, complete: true, missing: [], not_provided: [], version: 1,
      }),
    });
    await page.goto(url);
    await page.getByRole("button", { name: /برنامهٔ فضاها/ }).click();
    await page.getByLabel("تعداد واحدها (ضروری)").fill("2");
    await page.getByLabel("تعداد طبقات (ضروری)").fill("3");
    await page.getByRole("button", { name: "افزودن ردیف به اتاق‌ها و فضاها" }).click();
    await page.getByLabel("اتاق‌ها و فضاها 1: نوع فضا (ضروری)").selectOption("bedroom");
    await page.getByLabel("اتاق‌ها و فضاها 1: تعداد").fill("4");
    await page.getByRole("button", { name: "ذخیرهٔ نیازمندی‌ها" }).click();

    await expect(page.getByRole("status").filter({ hasText: "ذخیره شد؛ این بخش کامل است." })).toBeVisible();
    const put = state.requests.find((r) => r.key.endsWith("/requirements/program"));
    expect(put.headers["x-csrf-token"]).toBe("csrf-1");
    expect(put.body.version).toBe(0);
    expect(put.body.data).toMatchObject({
      units_count: "2",
      floors_count: "3",
      rooms: [{ kind: "bedroom", count: "4" }],
    });
  });

  test("an empty room list is sent explicitly as none", async ({ page }) => {
    const state = { loggedIn: true };
    await mockApi(page, state, {
      [`PUT /projects/${PROJECT.id}/requirements/program`]: ok({
        section: "program", data: {}, complete: false, missing: ["floors_count"], not_provided: [], version: 1,
      }),
    });
    await page.goto(url);
    await page.getByRole("button", { name: /برنامهٔ فضاها/ }).click();
    await page.getByLabel("تعداد واحدها (ضروری)").fill("1");
    await page.getByRole("button", { name: "ذخیرهٔ نیازمندی‌ها" }).click();
    await expect(page.getByRole("status").filter({ hasText: "تعداد طبقات" })).toBeVisible();
    const put = state.requests.find((r) => r.key.endsWith("/requirements/program"));
    expect(put.body.data.rooms).toEqual([]);
  });

  test("preferences keep constraints by level and report values not provided", async ({ page }) => {
    const state = {
      loggedIn: true,
      requirements: {
        preferences: { data: { style: "مدرن" }, complete: true, version: 1,
          not_provided: ["budget_amount", "budget_currency"] },
      },
    };
    await mockApi(page, state, {
      [`PUT /projects/${PROJECT.id}/requirements/preferences`]: ok({
        section: "preferences", data: {}, complete: true, missing: [], not_provided: [], version: 2,
      }),
    });
    await page.goto(url);
    await page.getByRole("button", { name: /ترجیحات و محدودیت‌ها/ }).click();
    await expect(page.getByTestId("preferences-not-provided")).toContainText("بودجهٔ هدف");
    await expect(page.getByLabel("بودجهٔ هدف")).toHaveValue("");
    await page.getByRole("button", { name: "افزودن ردیف به الزامات و محدودیت‌ها" }).click();
    await page.getByLabel("الزامات و محدودیت‌ها 1: سطح (ضروری)").selectOption("unacceptable");
    await page.getByLabel("الزامات و محدودیت‌ها 1: توضیح (ضروری)").fill("پنجرهٔ مشرف به همسایه");
    await page.getByRole("button", { name: "ذخیرهٔ نیازمندی‌ها" }).click();
    await expect(page.getByRole("status").filter({ hasText: "ذخیره شد" })).toBeVisible();
    const put = state.requests.find((r) => r.key.endsWith("/requirements/preferences"));
    expect(put.body.data.style).toBe("مدرن");
    expect(put.body.version).toBe(1);
    expect(put.body.data.constraints).toEqual([
      { level: "unacceptable", description: "پنجرهٔ مشرف به همسایه" },
    ]);
    // Untouched fields are sent empty; the API drops them, so they stay "not provided".
    expect(put.body.data.budget_amount ?? "").toBe("");
  });

  test("references keep label and explanation; list errors name the row", async ({ page }) => {
    await mockApi(page, { loggedIn: true }, {
      [`PUT /projects/${PROJECT.id}/requirements/references`]: (route) =>
        route
          .fulfill({
            status: 422,
            contentType: "application/json",
            body: JSON.stringify({ error: { code: "invalid_requirements", message: "x", correlation_id: "t",
              details: [{ field: "items[0].url", reason: "invalid_url" }] } }),
          })
          .then(() => true),
    });
    await page.goto(url);
    await page.getByRole("button", { name: /نمونه‌های مرجع/ }).click();
    await page.getByRole("button", { name: "افزودن ردیف به نمونه‌ها" }).click();
    await page.getByLabel("نمونه‌ها 1: برچسب (ضروری)").fill("نمای آجری");
    await page.getByLabel("نمونه‌ها 1: توضیح").fill("نمای مورد علاقه");
    await page.getByLabel("نمونه‌ها 1: پیوند").fill("ftp://x");
    await page.getByRole("button", { name: "ذخیرهٔ نیازمندی‌ها" }).click();
    await expect(page.getByText("ردیف 1 (url): پیوند باید با http:// یا https:// شروع شود.")).toBeVisible();
  });

  test("members without edit permission see requirements read-only", async ({ page }) => {
    await mockApi(page, {
      loggedIn: true,
      permissions: ["project.view"],
      requirements: { preferences: { data: { style: "کلاسیک" }, complete: true, version: 1, not_provided: [] } },
    });
    await page.goto(url);
    await page.getByRole("button", { name: /ترجیحات و محدودیت‌ها/ }).click();
    await expect(page.getByLabel("سبک معماری")).toHaveValue("کلاسیک");
    await expect(page.getByLabel("سبک معماری")).toBeDisabled();
    await expect(page.getByRole("button", { name: "ذخیرهٔ نیازمندی‌ها" })).toHaveCount(0);
  });
});

test.describe("environment inputs", () => {
  const url = `/projects/${PROJECT.id}`;
  const ok = (body) => (route) =>
    route
      .fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(body) })
      .then(() => true);

  test("an unsourced value is saved and shown as needing inquiry", async ({ page }) => {
    const state = { loggedIn: true };
    await mockApi(page, state, {
      [`PUT /projects/${PROJECT.id}/environment/rainfall`]: ok({
        field: "rainfall",
        data: { annual_mm: 290 },
        status: "needs_inquiry",
        source_missing: ["source_type", "source_title_or_reference", "location_reference", "source_date"],
        version: 1,
      }),
    });
    await page.goto(url);
    await page.getByRole("button", { name: /بارندگی/ }).click();
    await expect(page.getByTestId("env-status")).toHaveAttribute("data-status", "unknown");
    await page.getByLabel("بارش سالانه (میلی‌متر)").fill("290");
    await page.getByRole("button", { name: "ذخیرهٔ این مورد" }).click();
    await expect(page.getByRole("status").filter({ hasText: "ذخیره شد؛ وضعیت: نیازمند استعلام." })).toBeVisible();
    await expect(page.getByTestId("env-status")).toContainText("محل داده");
    const put = state.requests.find((r) => r.key.endsWith("/environment/rainfall"));
    expect(put.headers["x-csrf-token"]).toBe("csrf-1");
    expect(put.body.version).toBe(0);
    expect(put.body.data.annual_mm).toBe("290");
  });

  test("source, location and date are sent with the value", async ({ page }) => {
    const state = { loggedIn: true };
    await mockApi(page, state, {
      [`PUT /projects/${PROJECT.id}/environment/seismicity`]: ok({
        field: "seismicity", data: {}, status: "verified", source_missing: [], version: 1,
      }),
    });
    await page.goto(url);
    await page.getByRole("button", { name: /لرزه‌خیزی/ }).click();
    await page.getByLabel("شتاب مبنای طرح (برحسب g)").fill("0.35");
    await page.getByLabel("نوع مرجع داده").selectOption("national_standard");
    await page.getByLabel("عنوان مرجع داده").fill("استاندارد ۲۸۰۰");
    await page.getByLabel("محلی که داده به آن مربوط است").fill("تبریز");
    await page.getByLabel("تاریخ داده").fill("1403-12-01");
    await page.getByLabel("تقویم این تاریخ").selectOption("jalali");
    await page.getByLabel(/تأیید شده می‌دانم/).check();
    await page.getByRole("button", { name: "ذخیرهٔ این مورد" }).click();
    await expect(page.getByRole("status").filter({ hasText: "تأییدشده" })).toBeVisible();
    const put = state.requests.find((r) => r.key.endsWith("/environment/seismicity"));
    expect(put.body.data).toEqual({
      design_pga_g: "0.35",
      source_type: "national_standard",
      source_title: "استاندارد ۲۸۰۰",
      location_reference: "تبریز",
      source_date: "1403-12-01",
      source_calendar: "jalali",
      source_verified: true,
    });
  });

  test("utility availability is a choice and API errors show next to fields", async ({ page }) => {
    await mockApi(page, { loggedIn: true }, {
      [`PUT /projects/${PROJECT.id}/environment/gas`]: (route) =>
        route
          .fulfill({
            status: 422,
            contentType: "application/json",
            body: JSON.stringify({ error: { code: "invalid_environment", message: "x", correlation_id: "t",
              details: [{ field: "source_calendar", reason: "calendar_required" }] } }),
          })
          .then(() => true),
    });
    await page.goto(url);
    await page.getByRole("button", { name: /^گاز / }).click();
    await page.getByLabel("وضعیت دسترسی").selectOption("planned");
    await page.getByLabel("تاریخ داده").fill("1403-12-01");
    await page.getByRole("button", { name: "ذخیرهٔ این مورد" }).click();
    await expect(page.getByText("با تاریخ، تقویم آن را هم انتخاب کنید.")).toBeVisible();
    await expect(page.getByLabel("تقویم این تاریخ")).toHaveAttribute("aria-invalid", "true");
  });

  test("stored status shows what is missing; view-only members cannot edit", async ({ page }) => {
    await mockApi(page, {
      loggedIn: true,
      permissions: ["project.view"],
      environment: { wind: { data: { mean_speed_ms: 3 }, status: "needs_inquiry",
        source_missing: ["source_date"], version: 1 } },
    });
    await page.goto(url);
    await page.getByRole("button", { name: /باد غالب/ }).click();
    const status = page.getByTestId("env-status");
    await expect(status).toHaveAttribute("data-status", "needs_inquiry");
    await expect(status).toContainText("تاریخ داده");
    await expect(page.getByLabel("میانگین سرعت باد (متر بر ثانیه)")).toBeDisabled();
    await expect(page.getByRole("button", { name: "ذخیرهٔ این مورد" })).toHaveCount(0);
  });
});

test.describe("project files", () => {
  const url = `/projects/${PROJECT.id}`;
  const stored = (extra = {}) => ({
    id: "f-1",
    series_id: "s-1",
    version_number: 1,
    is_latest: true,
    is_basis: false,
    basis_outdated: false,
    sha256: "a".repeat(64),
    original_name: "survey.pdf",
    kind: "survey",
    document_date: "2026-05-01",
    ownership: "کارفرما",
    detected_type: "pdf",
    size_bytes: 2048,
    scan_status: "clean",
    scan_detail: null,
    uploaded_by_name: "کاربر",
    created_at: "2026-11-22T08:00:00Z",
    downloadable: true,
    ...extra,
  });

  test("a chosen file is sent as the raw body with its metadata in the query", async ({ page }) => {
    const state = { loggedIn: true };
    await mockApi(page, state, {
      [`POST /projects/${PROJECT.id}/files`]: (route) =>
        route
          .fulfill({ status: 201, contentType: "application/json", body: JSON.stringify(stored()) })
          .then(() => true),
    });
    await page.goto(url);
    await page.getByLabel("فایل", { exact: true }).setInputFiles({
      name: "survey.pdf",
      mimeType: "application/pdf",
      buffer: Buffer.from("%PDF-1.4 test"),
    });
    await page.getByLabel("نوع سند").selectOption("survey");
    await page.getByLabel("تاریخ سند").fill("2026-05-01");
    await page.getByLabel("مالک سند").fill("کارفرما");
    await page.getByRole("button", { name: "بارگذاری فایل" }).click();
    await expect(page.getByRole("status").filter({ hasText: "فایل بارگذاری شد." })).toBeVisible();

    const post = state.requests.find((r) => r.key === `POST /projects/${PROJECT.id}/files`);
    const query = new URLSearchParams(post.query);
    expect(query.get("filename")).toBe("survey.pdf");
    expect(query.get("kind")).toBe("survey");
    expect(query.get("document_date")).toBe("2026-05-01");
    expect(query.get("ownership")).toBe("کارفرما");
    expect(post.headers["content-type"]).toBe("application/octet-stream");
    expect(post.headers["x-csrf-token"]).toBe("csrf-1");
    expect(post.raw.toString()).toBe("%PDF-1.4 test");
  });

  test("a file and a document kind are required before anything is sent", async ({ page }) => {
    const state = { loggedIn: true };
    await mockApi(page, state);
    await page.goto(url);
    await page.getByRole("button", { name: "بارگذاری فایل" }).click();
    await expect(page.getByText("یک فایل انتخاب کنید.")).toBeVisible();
    expect(state.requests.some((r) => r.key.startsWith("POST") && r.key.endsWith("/files"))).toBe(false);
  });

  test("API rejections are explained in Persian", async ({ page }) => {
    await mockApi(page, { loggedIn: true }, {
      [`POST /projects/${PROJECT.id}/files`]: (route) =>
        route
          .fulfill({
            status: 415,
            contentType: "application/json",
            body: JSON.stringify({ error: { code: "unsupported_type", message: "x", correlation_id: "t" } }),
          })
          .then(() => true),
    });
    await page.goto(url);
    await page.getByLabel("فایل", { exact: true }).setInputFiles({
      name: "a.pdf", mimeType: "application/pdf", buffer: Buffer.from("MZ"),
    });
    await page.getByLabel("نوع سند").selectOption("other");
    await page.getByRole("button", { name: "بارگذاری فایل" }).click();
    await expect(page.getByText("این نوع فایل مجاز نیست.", { exact: false })).toBeVisible();
  });

  test("clean files have a download link; quarantined files do not", async ({ page }) => {
    await mockApi(page, {
      loggedIn: true,
      files: [
        stored(),
        stored({ id: "f-2", original_name: "bad.pdf", scan_status: "quarantined",
          scan_detail: "eicar_test_signature", downloadable: false }),
      ],
    });
    await page.goto(url);
    const link = page.getByRole("link", { name: "دانلود survey.pdf" });
    await expect(link).toHaveAttribute("href", `/api/v1/projects/${PROJECT.id}/files/f-1/download`);
    await expect(page.getByRole("link", { name: "دانلود bad.pdf" })).toHaveCount(0);
    await expect(page.getByText("قرنطینه")).toBeVisible();
    await expect(page.getByText("قابل دانلود نیست")).toBeVisible();
  });

  test("deleting a file asks the API and reloads the list", async ({ page }) => {
    const state = { loggedIn: true, files: [stored()] };
    await mockApi(page, state, {
      [`DELETE /projects/${PROJECT.id}/files/f-1`]: (route) => {
        state.files = [];
        return route.fulfill({ status: 204 }).then(() => true);
      },
    });
    await page.goto(url);
    await page.getByRole("button", { name: "حذف survey.pdf" }).click();
    await expect(page.getByText("هنوز فایلی بارگذاری نشده است.")).toBeVisible();
    const del = state.requests.find((r) => r.key.startsWith("DELETE"));
    expect(del.headers["x-csrf-token"]).toBe("csrf-1");
  });

  test("versions: a new version, restore, comparison and the takeoff basis", async ({ page }) => {
    const v1 = stored({ id: "f-1", version_number: 1, is_latest: false, is_basis: true,
      basis_outdated: true });
    const v2 = stored({ id: "f-2", version_number: 2 });
    const state = { loggedIn: true, files: [v2, v1] };
    await mockApi(page, state, {
      [`POST /projects/${PROJECT.id}/files`]: (route) =>
        route
          .fulfill({ status: 201, contentType: "application/json",
            body: JSON.stringify(stored({ id: "f-3", version_number: 3 })) })
          .then(() => true),
      [`POST /projects/${PROJECT.id}/files/f-1/restore`]: (route) =>
        route
          .fulfill({ status: 201, contentType: "application/json",
            body: JSON.stringify(stored({ id: "f-4", version_number: 3 })) })
          .then(() => true),
      [`PUT /projects/${PROJECT.id}/files/f-2/basis`]: (route) =>
        route
          .fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(v2) })
          .then(() => true),
      [`GET /projects/${PROJECT.id}/files/f-1/compare/f-2`]: (route) =>
        route
          .fulfill({ status: 200, contentType: "application/json",
            body: JSON.stringify({ identical_content: false, size_delta_bytes: 1024,
              type_changed: false }) })
          .then(() => true),
    });
    await page.goto(url);
    await expect(page.getByText("نسخهٔ جدیدتری از این فایل آمده است", { exact: false })).toBeVisible();
    await expect(page.getByText("مبنای متره و برآورد", { exact: false })).toBeVisible();

    await page.getByRole("button", { name: "مقایسه نسخهٔ 1", exact: false }).click();
    await expect(page.getByText("محتوا تغییر کرده است", { exact: false })).toBeVisible();

    await page.getByRole("button", { name: "ثبت نسخهٔ 2", exact: false }).click();
    expect(state.requests.find((r) => r.key.startsWith("PUT")).body).toEqual({ is_basis: true });

    await page.getByRole("button", { name: "بازیابی نسخهٔ 1", exact: false }).click();
    await expect(page.getByText("بازیابی شد", { exact: false })).toBeVisible();

    await page.getByLabel("فایل", { exact: true }).setInputFiles({
      name: "survey.pdf", mimeType: "application/pdf", buffer: Buffer.from("%PDF-1.4 v3"),
    });
    await page.getByLabel("نوع سند").selectOption("survey");
    await page.getByLabel("نسخهٔ جدید از فایل").selectOption("f-2");
    await page.getByRole("button", { name: "بارگذاری فایل" }).click();
    await expect(page.getByText("نسخه‌های قبلی نگه داشته شد", { exact: false })).toBeVisible();
    const post = state.requests.find((r) => r.key === `POST /projects/${PROJECT.id}/files`);
    expect(new URLSearchParams(post.query).get("new_version_of")).toBe("f-2");
  });

  test("members without upload permission see the list but no upload form", async ({ page }) => {
    await mockApi(page, { loggedIn: true, permissions: ["project.view"], files: [stored()] });
    await page.goto(url);
    await expect(page.getByRole("link", { name: "دانلود survey.pdf" })).toBeVisible();
    await expect(page.getByRole("button", { name: "بارگذاری فایل" })).toHaveCount(0);
    await expect(page.getByRole("button", { name: "حذف survey.pdf" })).toHaveCount(0);
  });
});

test.describe("project invitations", () => {
  test("the owner invites by email, sees the pending invitation and can revoke it", async ({
    page,
  }) => {
    const state = { loggedIn: true, invitations: [] };
    await mockApi(page, state, {
      [`POST /projects/${PROJECT.id}/invitations`]: (route, request) => {
        const body = request.postDataJSON();
        if (body.email === "member@example.com") {
          return route
            .fulfill({
              status: 409,
              contentType: "application/json",
              body: JSON.stringify(error("already_in_organization")),
            })
            .then(() => true);
        }
        state.invitations = [
          { id: "i-1", email: body.email, role: body.role, expires_at: "2026-12-01T00:00:00+00:00" },
        ];
        return route
          .fulfill({
            status: 201,
            contentType: "application/json",
            body: JSON.stringify({
              invitation: state.invitations[0],
              token: "tok-1",
              email_sent: true,
            }),
          })
          .then(() => true);
      },
      [`DELETE /projects/${PROJECT.id}/invitations/i-1`]: (route) => {
        state.invitations = [];
        return route.fulfill({ status: 204 }).then(() => true);
      },
    });
    await page.goto(`/projects/${PROJECT.id}`);

    await page.getByLabel("ایمیل فرد دعوت‌شده به پروژه").fill("member@example.com");
    await page.getByRole("button", { name: "ساخت دعوت‌نامهٔ پروژه" }).click();
    await expect(page.getByRole("alert").filter({ hasText: "عضو سازمان است" })).toBeVisible();

    await page.getByLabel("ایمیل فرد دعوت‌شده به پروژه").fill("new@example.com");
    await page.getByLabel("نقش فرد دعوت‌شده در پروژه").first().selectOption("structural_engineer");
    await page.getByRole("button", { name: "ساخت دعوت‌نامهٔ پروژه" }).click();
    await expect(page.locator("#project-invite-link")).toHaveValue(/\/invitations\/accept\?token=tok-1$/);
    await expect(page.getByText("ایمیل دعوت ارسال شد.")).toBeVisible();
    const created = state.requests.filter((r) => r.key === `POST /projects/${PROJECT.id}/invitations`).at(-1);
    expect(created.body).toEqual({ email: "new@example.com", role: "structural_engineer" });
    expect(created.headers["x-csrf-token"]).toBe("csrf-1");
    await expect(page.getByRole("button", { name: "لغو دعوت new@example.com" })).toBeVisible();

    await page.getByRole("button", { name: "لغو دعوت new@example.com" }).click();
    await expect(page.getByRole("button", { name: "لغو دعوت new@example.com" })).toHaveCount(0);
  });

  test("accepting a project invitation links to the project", async ({ page }) => {
    await mockApi(page, { loggedIn: true }, {
      "POST /invitations/accept": (route) =>
        route
          .fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify({ organization_id: "o-1", org_role: "member", project_id: PROJECT.id }),
          })
          .then(() => true),
    });
    await page.goto("/invitations/accept?token=abc");
    await page.getByRole("button", { name: "پذیرش دعوت" }).click();
    await expect(page.getByText("دعوت پروژه پذیرفته شد.")).toBeVisible();
    await expect(page.getByRole("link", { name: "رفتن به پروژه" })).toHaveAttribute(
      "href",
      `/projects/${PROJECT.id}`,
    );
  });
});

test.describe("email verification", () => {
  test("registration asks the person to confirm the email instead of signing in", async ({
    page,
  }) => {
    const state = { loggedIn: false };
    await mockApi(page, state, {
      "POST /auth/register": (route) =>
        route
          .fulfill({
            status: 201,
            contentType: "application/json",
            body: JSON.stringify({
              user: { id: "u-1", email: "ali@example.com", display_name: "علی", is_system_admin: false },
              verification_required: true,
            }),
          })
          .then(() => true),
      "POST /auth/email-verification/request": (route) =>
        route.fulfill({ status: 202, contentType: "application/json", body: '{"status":"accepted"}' }).then(() => true),
    });
    await page.goto("/register");
    await page.getByLabel("نام و نام خانوادگی").fill("علی");
    await page.getByLabel("ایمیل").fill("ali@example.com");
    await page.getByLabel("رمز عبور").fill("a long passphrase 1");
    await page.getByRole("button", { name: "ایجاد حساب" }).click();
    await expect(page.getByText(/پیوند تأیید به ali@example.com ارسال شد/)).toBeVisible();
    expect(state.requests.some((r) => r.key === "POST /auth/login")).toBe(false);

    await page.getByRole("button", { name: "ارسال دوباره ایمیل تأیید" }).click();
    await expect(page.getByText(/اگر این ایمیل تأییدنشده باشد/)).toBeVisible();
    const resend = state.requests.find((r) => r.key === "POST /auth/email-verification/request");
    expect(resend.body).toEqual({ email: "ali@example.com" });
  });

  test("an unverified login offers to resend the confirmation email", async ({ page }) => {
    await mockApi(page, { loggedIn: false }, {
      "POST /auth/login": (route) =>
        route
          .fulfill({
            status: 403,
            contentType: "application/json",
            body: JSON.stringify(error("email_not_verified")),
          })
          .then(() => true),
      "POST /auth/email-verification/request": (route) =>
        route.fulfill({ status: 202, contentType: "application/json", body: '{"status":"accepted"}' }).then(() => true),
    });
    await page.goto("/login");
    await page.getByLabel("ایمیل").fill("ali@example.com");
    await page.getByLabel("رمز عبور").fill("a long passphrase 1");
    await page.getByRole("button", { name: "ورود", exact: true }).click();
    await expect(page.getByRole("alert").filter({ hasText: "تأیید نشده" })).toBeVisible();
    await page.getByRole("button", { name: "ارسال دوباره ایمیل تأیید" }).click();
    await expect(page.getByText(/پیوند تأیید دوباره/)).toBeVisible();
  });

  test("the confirmation link needs a click and shows API refusals", async ({ page }) => {
    const state = { loggedIn: false };
    await mockApi(page, state, {
      "POST /auth/email-verification/confirm": (route, request) => {
        const ok = request.postDataJSON().token === "good";
        return route
          .fulfill(
            ok
              ? { status: 204 }
              : { status: 400, contentType: "application/json", body: JSON.stringify(error("invalid_token")) },
          )
          .then(() => true);
      },
    });
    await page.goto("/verify-email?token=bad");
    expect(state.requests.some((r) => r.key.includes("email-verification/confirm"))).toBe(false);
    await page.getByRole("button", { name: "تأیید ایمیل" }).click();
    await expect(page.getByRole("alert").filter({ hasText: "نامعتبر" })).toBeVisible();

    await page.goto("/verify-email?token=good");
    await page.getByRole("button", { name: "تأیید ایمیل" }).click();
    await expect(page.getByText("ایمیل شما تأیید شد.")).toBeVisible();
    await expect(page.getByRole("link", { name: "رفتن به ورود" })).toBeVisible();

    await page.goto("/verify-email");
    await expect(page.getByRole("alert").filter({ hasText: "ناقص" })).toBeVisible();
  });
});
