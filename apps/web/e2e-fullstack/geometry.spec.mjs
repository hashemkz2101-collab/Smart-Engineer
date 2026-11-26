import { expect, test } from "@playwright/test";

// New Phase 2 scenario only; the existing Phase 1 workflows are not rerun.
test("geometry edits persist, units do not mutate metres and setbacks need a source", async ({ page }) => {
  const email = `geometry-${Date.now()}@example.com`;
  await page.goto("/register");
  await page.getByLabel("نام و نام خانوادگی").fill("آزمون هندسه");
  await page.getByLabel("ایمیل", { exact: true }).fill(email);
  await page.getByLabel("رمز عبور", { exact: true }).fill("a long passphrase 1");
  await page.getByRole("button", { name: "ایجاد حساب", exact: true }).click();
  await expect(page).toHaveURL(/\/projects$/);
  await page.getByLabel("نام پروژه", { exact: true }).fill("زمین هندسی آزمایشی");
  await page.getByRole("button", { name: "ایجاد پروژه", exact: true }).click();
  const editor = page.getByTestId("geometry-editor");
  await editor.getByRole("button", { name: "ساخت مستطیل ۱۰×۲۰ متر" }).click();
  await expect(editor.getByTestId("geometry-report")).toContainText("۲۰۰");
  await editor.getByLabel("واحد نمایش بوم").selectOption("cm");
  await expect(editor.getByLabel("X رأس 2 (cm)")).toHaveValue("1000");
  await editor.getByLabel("واحد نمایش بوم").selectOption("mm");
  await expect(editor.getByLabel("Y رأس 3 (mm)")).toHaveValue("20000");
  await editor.getByLabel("واحد نمایش بوم").selectOption("m");
  await editor.getByLabel("X رأس 2 (m)").fill("12");
  await expect(editor.getByTestId("geometry-report")).toContainText("۲۲۰");
  for (const [index, role] of ["front", "right", "rear", "left"].entries()) {
    await editor.getByLabel(`نوع ضلع ${index + 1}`, { exact: true }).selectOption(role);
  }
  const section = page.locator("form").filter({ has: editor });
  await section.getByRole("button", { name: "ذخیرهٔ این بخش", exact: true }).click();
  await expect(page.getByText("ذخیره شد؛ این بخش کامل است.", { exact: true })).toBeVisible();
  await page.reload();
  await expect(editor.getByLabel("X رأس 2 (m)")).toHaveValue("12");
  await expect(editor.getByTestId("geometry-report")).toContainText("۲۲۰");
  await expect(editor.getByTestId("buildable-boundary")).toHaveCount(0);
  await page.getByRole("button", { name: /عقب‌نشینی و اصلاحی/ }).click();
  for (const label of ["جلو", "عقب", "چپ", "راست"]) {
    await page.getByLabel(`عقب‌نشینی از ${label} (متر)`, { exact: true }).fill("1");
  }
  await page.getByRole("button", { name: "ذخیرهٔ این ضابطه", exact: true }).click();
  await page.reload();
  await expect(editor.getByTestId("buildable-boundary")).toHaveCount(0);
  // Keyboard editing is an equivalent alternative to pointer dragging.
  await editor.getByRole("button", { name: "رأس 2", exact: true }).focus();
  await page.keyboard.press("ArrowRight");
  await expect(editor.getByLabel("X رأس 2 (m)")).toHaveValue("13");
  await section.getByRole("button", { name: "ذخیرهٔ این بخش", exact: true }).click();
  await page.getByRole("button", { name: /عقب‌نشینی و اصلاحی/ }).click();
  await page.getByLabel("نوع منبع", { exact: true }).selectOption("municipality_letter");
  await page.getByLabel("عنوان منبع", { exact: true }).fill("منبع مصنوعی آزمون، نه ضابطهٔ واقعی");
  await page.getByLabel("تاریخ منبع", { exact: true }).fill("2026-11-25");
  await page.getByLabel("تقویم تاریخ", { exact: true }).selectOption("gregorian");
  await page.getByLabel("شماره یا ویرایش منبع", { exact: true }).fill("synthetic-v1");
  await page.getByLabel("آغاز اعتبار منبع (میلادی)", { exact: true }).fill("2020-01-01");
  await page.getByLabel("پایان اعتبار منبع (میلادی)", { exact: true }).fill("2099-12-31");
  await page.getByLabel("تأیید می‌کنم این منبع مقدار بالا را تأیید می‌کند", { exact: true }).check();
  await page.getByRole("button", { name: "ذخیرهٔ این ضابطه", exact: true }).click();
  await expect(page.getByText("ذخیره شد؛ وضعیت: تأییدشده.", { exact: true })).toBeVisible();
  await page.reload();
  await expect(editor.getByTestId("buildable-boundary")).toHaveCount(1);
  await expect(editor.getByTestId("geometry-report")).toContainText("محاسبهٔ اولیه");
});
