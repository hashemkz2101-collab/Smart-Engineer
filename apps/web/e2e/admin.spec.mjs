import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

import { error, mockApi, USER } from "./api-mock.mjs";

const ADMIN = { ...USER, is_system_admin: true };
const json = (route, status, body) =>
  route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) });

const OTHER = {
  id: "u-2",
  email: "sara@example.com",
  display_name: "سارا احمدی",
  is_active: true,
  is_system_admin: false,
  last_login_at: null,
  created_at: null,
};
const SELF = { ...OTHER, id: "u-1", email: USER.email, display_name: USER.display_name, is_system_admin: true };
const PROJECT = {
  id: "p-9",
  name: "ویلای شمال",
  project_type: "residential_house",
  status: "active",
  organization_id: "o-9",
  organization_name: "دفتر نمونه",
  member_count: 1,
  created_at: null,
};

function adminOverrides(state) {
  state.users = [SELF, { ...OTHER }];
  state.members = [
    { user_id: "u-3", email: "owner@example.com", display_name: "مالک", role: "owner" },
  ];
  return {
    "GET /auth/me": (route) =>
      json(route, 200, { user: ADMIN, csrf_token: "csrf-1" }).then(() => true),
    "GET /admin/users": (route) => json(route, 200, { users: state.users }).then(() => true),
    "PUT /admin/users/u-2/active": (route, request) => {
      state.users[1] = { ...state.users[1], is_active: request.postDataJSON().active };
      return json(route, 200, { user: state.users[1] }).then(() => true);
    },
    "PUT /admin/users/u-2/system-admin": (route, request) => {
      state.users[1] = { ...state.users[1], is_system_admin: request.postDataJSON().is_system_admin };
      return json(route, 200, { user: state.users[1] }).then(() => true);
    },
    "GET /admin/projects": (route) => json(route, 200, { projects: [PROJECT] }).then(() => true),
    "GET /admin/projects/p-9/members": (route) =>
      json(route, 200, { members: state.members }).then(() => true),
    "POST /admin/projects/p-9/members": (route, request) => {
      const body = request.postDataJSON();
      if (body.email === "stranger@example.com") {
        return json(route, 422, error("user_not_in_organization")).then(() => true);
      }
      state.members = [
        ...state.members,
        { user_id: "u-2", email: body.email, display_name: "سارا احمدی", role: body.role },
      ];
      return json(route, 201, { member: { user_id: "u-2", role: body.role } }).then(() => true);
    },
    "GET /admin/audit": (route) =>
      json(route, 200, {
        events: [
          {
            id: 2,
            action: "admin.user_deactivated",
            actor_email: USER.email,
            target_email: OTHER.email,
            target_project_id: null,
            detail: null,
            created_at: "2026-11-22T10:00:00+00:00",
          },
        ],
      }).then(() => true),
  };
}

test.describe("system administration", () => {
  test("ordinary users see no admin link and a not-found page", async ({ page }) => {
    const state = { loggedIn: true };
    await mockApi(page, state);
    await page.goto("/projects");
    await expect(page.getByRole("link", { name: "مدیریت سیستم" })).toHaveCount(0);
    await page.goto("/admin");
    await expect(page.getByRole("heading", { level: 1 })).toHaveText("صفحه پیدا نشد");
    expect(state.requests.filter((r) => r.key.includes("/admin/"))).toEqual([]);
  });

  test("an administrator deactivates a user and grants the admin role", async ({ page }) => {
    const state = { loggedIn: true };
    await mockApi(page, state, adminOverrides(state));
    await page.goto("/admin");
    await expect(page.getByRole("heading", { level: 1 })).toHaveText("مدیریت سیستم");
    await expect(page.getByText("حساب شما")).toBeVisible();

    await page.getByRole("button", { name: "غیرفعال‌سازی سارا احمدی" }).click();
    await expect(page.getByRole("button", { name: "فعال‌سازی سارا احمدی" })).toBeVisible();
    const call = state.requests.find((r) => r.key === "PUT /admin/users/u-2/active");
    expect(call.body).toEqual({ active: false });
    expect(call.headers["x-csrf-token"]).toBe("csrf-1");

    await page.getByRole("button", { name: "دادن دسترسی مدیر به سارا احمدی" }).click();
    await expect(page.getByRole("button", { name: "گرفتن دسترسی مدیر از سارا احمدی" })).toBeVisible();
  });

  test("project access can be added, with API refusals shown in Persian", async ({ page }) => {
    const state = { loggedIn: true };
    await mockApi(page, state, adminOverrides(state));
    await page.goto("/admin");
    await page.getByRole("button", { name: "پروژه‌ها", exact: true }).click();
    await page.getByRole("button", { name: "مدیریت دسترسی ویلای شمال" }).click();
    await expect(page.getByText("owner@example.com")).toBeVisible();

    await page.getByLabel("ایمیل عضو جدید ویلای شمال").fill("stranger@example.com");
    await page.getByRole("button", { name: "افزودن عضو" }).click();
    await expect(page.getByRole("alert").filter({ hasText: "عضو سازمان نیست" })).toBeVisible();

    await page.getByLabel("ایمیل عضو جدید ویلای شمال").fill("sara@example.com");
    await page.getByLabel("نقش عضو جدید ویلای شمال").selectOption("architect");
    await page.getByRole("button", { name: "افزودن عضو" }).click();
    await expect(page.getByText("sara@example.com")).toBeVisible();
    const add = state.requests.filter((r) => r.key === "POST /admin/projects/p-9/members").at(-1);
    expect(add.body).toEqual({ email: "sara@example.com", role: "architect" });
  });

  test("the audit tab lists actions in Persian and the page passes axe", async ({ page }) => {
    const state = { loggedIn: true };
    await mockApi(page, state, adminOverrides(state));
    await page.goto("/admin");
    await page.getByRole("button", { name: "ممیزی" }).click();
    await expect(page.getByText("حساب کاربر غیرفعال شد")).toBeVisible();
    const results = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"])
      .analyze();
    expect(results.violations).toEqual([]);
  });
});
