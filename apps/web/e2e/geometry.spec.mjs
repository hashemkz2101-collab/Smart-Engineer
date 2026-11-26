import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

import { mockApi, OWNER_PERMISSIONS, PROJECT } from "./api-mock.mjs";

const initial = { shape: "rectangular", width_m: 10, depth_m: 20, geometry_reference: "local_cartesian" };
function report(data) {
  const vertices = data.shape === "rectangular"
    ? [{ x: 0, y: 0 }, { x: Number(data.width_m), y: 0 }, { x: Number(data.width_m), y: Number(data.depth_m) }, { x: 0, y: Number(data.depth_m) }]
    : (data.vertices ?? []).map((p) => ({ x: Number(p.x), y: Number(p.y) }));
  // Test-fixture geometry, not a production solver. Real values have Python/API tests.
  const area = Math.abs(vertices.reduce((sum, p, i) => {
    const q = vertices[(i + 1) % vertices.length]; return sum + p.x * q.y - p.y * q.x;
  }, 0)) / 2;
  const edges = vertices.map((p, i) => {
    const q = vertices[(i + 1) % vertices.length];
    return { index: i, length_m: Math.hypot(q.x - p.x, q.y - p.y), local_bearing_deg: 0, north_bearing_deg: null };
  });
  return { status: "valid", vertices, area_m2: area,
    perimeter_m: edges.reduce((sum, edge) => sum + edge.length_m, 0), edges,
    north_angle_deg: null, orientation: "counterclockwise", engine_version: "fixture-only",
    canonical_data: data, source_versions: { parcel: 1, access: 0, setbacks: 0, coverage: 0 },
    envelope: { status: "needs_inquiry", reasons: ["source_not_verified"], polygons: [], area_m2: null, max_footprint_m2: null } };
}
async function setup(page, { readOnly = false, conflict = false } = {}) {
  const state = { loggedIn: true, permissions: readOnly ? ["project.view"] : OWNER_PERMISSIONS,
    site: { parcel: { data: structuredClone(initial), version: 1, complete: true } } };
  await mockApi(page, state, {
    [`GET /projects/${PROJECT.id}/geometry`]: async (route) => {
      await route.fulfill({ json: report(state.site.parcel.data) }); return true;
    },
    [`POST /projects/${PROJECT.id}/geometry/preview`]: async (route, request) => {
      await route.fulfill({ json: report(request.postDataJSON().data) }); return true;
    },
    [`PUT /projects/${PROJECT.id}/site/parcel`]: async (route, request) => {
      if (conflict) {
        await route.fulfill({ status: 409, json: { error: { code: "version_conflict" } } });
      } else {
        state.site.parcel = { data: request.postDataJSON().data, version: 2, complete: true,
          missing: [], not_provided: [], section: "parcel", derived: undefined };
        await route.fulfill({ json: state.site.parcel });
      }
      return true;
    },
  });
  await page.goto(`/projects/${PROJECT.id}`);
  const editor = page.getByTestId("geometry-editor");
  await expect(editor.getByTestId("geometry-report")).toContainText("۲۰۰");
  return { editor, state };
}

test("geometry units, keyboard and pointer edits share the same saved boundary", async ({ page }) => {
  const { editor, state } = await setup(page);
  await editor.getByLabel("واحد نمایش بوم").selectOption("cm");
  await expect(editor.getByLabel("X رأس 2 (cm)")).toHaveValue("1000");
  await editor.getByLabel("واحد نمایش بوم").selectOption("mm");
  await expect(editor.getByLabel("Y رأس 3 (mm)")).toHaveValue("20000");
  await editor.getByLabel("واحد نمایش بوم").selectOption("m");
  const vertex = editor.getByRole("button", { name: "رأس 2", exact: true });
  await vertex.focus(); await page.keyboard.press("ArrowRight");
  await expect(editor.getByLabel("X رأس 2 (m)")).toHaveValue("11");
  const box = await vertex.boundingBox();
  await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
  await page.mouse.down(); await page.mouse.move(box.x + box.width / 2 + 12, box.y + box.height / 2, { steps: 3 }); await page.mouse.up();
  await expect.poll(async () => Number(await editor.getByLabel("X رأس 2 (m)").inputValue())).toBeGreaterThan(11);
  const before = Number(await editor.getByLabel("X رأس 2 (m)").inputValue());
  const form = page.locator("form").filter({ has: editor });
  await form.getByRole("button", { name: "ذخیرهٔ این بخش", exact: true }).click();
  await expect.poll(() => state.site.parcel.version).toBe(2);
  expect(Number(state.site.parcel.data.vertices[1].x)).toBeCloseTo(before, 6);
});

test("409 preserves a geometry draft until the explicit reload action", async ({ page }) => {
  const { editor } = await setup(page, { conflict: true });
  await editor.getByLabel("X رأس 2 (m)").fill("12");
  const form = page.locator("form").filter({ has: editor });
  await form.getByRole("button", { name: "ذخیرهٔ این بخش", exact: true }).click();
  await expect(form.getByText("پیش‌نویس شما حفظ شده است.", { exact: false })).toBeVisible();
  await expect(editor.getByLabel("X رأس 2 (m)")).toHaveValue("12");
  await expect(editor.getByTestId("geometry-report")).toContainText("۲۲۰");
  await expect(form.getByRole("button", { name: "ذخیرهٔ این بخش", exact: true })).toBeDisabled();
  await expect(form.getByRole("button", { name: "بارگیری نسخهٔ جدید و کنار گذاشتن پیش‌نویس" })).toBeVisible();
});

test("read-only users can inspect geometry but cannot edit or preview it", async ({ page }) => {
  const { editor, state } = await setup(page, { readOnly: true });
  await expect(editor.getByLabel("X رأس 2 (m)")).toBeDisabled();
  await expect(editor.getByRole("button", { name: "افزودن رأس", exact: true })).toHaveCount(0);
  await editor.getByLabel("واحد نمایش بوم").selectOption("cm");
  await expect(editor.getByLabel("X رأس 2 (cm)")).toHaveValue("1000");
  expect(state.requests.some((r) => r.key.endsWith("/geometry/preview"))).toBe(false);
});

test("geometry sheet fits RTL mobile and dark theme and has no axe violations", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 812 });
  const { editor } = await setup(page);
  await page.getByRole("button", { name: /فعال‌کردن پوستهٔ تاریک/ }).click();
  await expect(page.locator("html")).toHaveAttribute("dir", "rtl");
  await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await editor.scrollIntoViewIfNeeded();
  const results = await new AxeBuilder({ page }).include('[data-testid="geometry-editor"]').analyze();
  expect(results.violations).toEqual([]);
});
