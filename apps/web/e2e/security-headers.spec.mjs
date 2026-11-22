import { expect, test } from "@playwright/test";

import { mockApi } from "./api-mock.mjs";

test("pages are served with defensive headers and cannot be framed", async ({ page }) => {
  await mockApi(page, {});
  const response = await page.goto("/");
  const headers = response.headers();
  expect(headers["x-content-type-options"]).toBe("nosniff");
  expect(headers["x-frame-options"]).toBe("DENY");
  expect(headers["referrer-policy"]).toBe("strict-origin-when-cross-origin");
  expect(headers["permissions-policy"]).toContain("camera=()");
  expect(headers["content-security-policy"]).toContain("frame-ancestors 'none'");
  expect(headers["x-powered-by"]).toBeUndefined();
});

test("the CSP does not break the app: pages render and no policy violation is logged", async ({
  page,
}) => {
  const problems = [];
  page.on("console", (message) => {
    if (/content security policy|refused to/i.test(message.text())) problems.push(message.text());
  });
  await mockApi(page, {});
  await page.goto("/login");
  await expect(page.getByRole("button", { name: "ورود", exact: true })).toBeVisible();
  await page.getByLabel("ایمیل").fill("a@example.com");
  expect(problems).toEqual([]);
});
