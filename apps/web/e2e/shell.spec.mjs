import { expect, test } from "@playwright/test";

const THEME_KEY = "smart-engineer-theme";

test.describe("Persian RTL shell", () => {
  test("renders RTL Persian landmarks and the not-yet-implemented notice", async ({ page }) => {
    await page.goto("/");

    await expect(page.locator("html")).toHaveAttribute("lang", "fa-IR");
    await expect(page.locator("html")).toHaveAttribute("dir", "rtl");
    await expect(page.getByRole("banner")).toBeVisible();
    await expect(page.getByRole("main")).toBeVisible();
    await expect(page.getByRole("contentinfo")).toBeVisible();
    await expect(page.getByRole("heading", { level: 1 })).toHaveText("به Smart Engineer خوش آمدید");
    await expect(page.getByText(/برآورد هنوز\s+پیاده‌سازی نشده‌اند/)).toBeVisible();
  });

  test("the brand sits at the inline start (right) and the actions at the end (left)", async ({
    page,
  }) => {
    await page.goto("/");

    const brand = await page.locator(".brand").boundingBox();
    const toggle = await page.getByRole("button", { name: /پوستهٔ|تغییر پوسته/ }).boundingBox();

    expect(brand.x).toBeGreaterThan(toggle.x);
  });

  test("unknown routes render the Persian not-found page with a way home", async ({ page }) => {
    const response = await page.goto("/no-such-page-p0-08");

    expect(response.status()).toBe(404);
    await expect(page.getByText("این نشانی در دسترس نیست")).toBeVisible();
    await page.getByRole("link", { name: "بازگشت به صفحهٔ اصلی" }).click();
    await expect(page).toHaveURL(/\/$/);
  });
});

test.describe("responsive layout", () => {
  for (const width of [320, 375, 768, 1024, 1440]) {
    for (const scheme of ["light", "dark"]) {
      test(`no horizontal overflow at ${width}px (${scheme})`, async ({ page }) => {
        await page.emulateMedia({ colorScheme: scheme });
        await page.setViewportSize({ width, height: 800 });
        await page.goto("/");

        const overflow = await page.evaluate(
          () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
        );
        expect(overflow).toBeLessThanOrEqual(0);

        for (const locator of [
          page.getByRole("heading", { level: 1 }),
          page.getByRole("button", { name: /پوسته/ }),
          page.getByRole("link", { name: "نمای کلی" }),
        ]) {
          await expect(locator).toBeVisible();
          const box = await locator.boundingBox();
          expect(box.x).toBeGreaterThanOrEqual(0);
          expect(box.x + box.width).toBeLessThanOrEqual(width);
        }
      });
    }
  }

  test("interactive targets are at least 24x24 CSS pixels (WCAG 2.2 target size)", async ({
    page,
  }) => {
    await page.goto("/");

    for (const locator of [
      page.getByRole("button", { name: /پوسته/ }),
      page.getByRole("link", { name: "نمای کلی" }),
      page.locator(".brand"),
    ]) {
      const box = await locator.boundingBox();
      expect(box.width).toBeGreaterThanOrEqual(24);
      expect(box.height).toBeGreaterThanOrEqual(24);
    }
  });
});

test.describe("keyboard operation", () => {
  test.skip(({ isMobile }) => isMobile, "Tab-key navigation is a desktop/keyboard check");

  test("the first Tab stop is a visible skip link that moves focus to the main content", async ({
    page,
  }) => {
    await page.goto("/");
    await page.keyboard.press("Tab");

    const skipLink = page.getByRole("link", { name: "رفتن به محتوای اصلی" });
    await expect(skipLink).toBeFocused();
    const box = await skipLink.boundingBox();
    expect(box.y).toBeGreaterThanOrEqual(0);
    expect(box.x).toBeGreaterThanOrEqual(0);

    await page.keyboard.press("Enter");
    await expect(page.locator("#main-content")).toBeFocused();
  });

  test("brand, navigation, and theme toggle are reachable in order with a visible focus ring", async ({
    page,
  }) => {
    await page.goto("/");
    const order = [
      page.getByRole("link", { name: "رفتن به محتوای اصلی" }),
      page.locator(".brand"),
      page.getByRole("link", { name: "نمای کلی" }),
      page.getByRole("button", { name: /پوسته/ }),
    ];

    for (const locator of order) {
      await page.keyboard.press("Tab");
      await expect(locator).toBeFocused();
      const outline = await locator.evaluate((element) => {
        const style = getComputedStyle(element);
        return { style: style.outlineStyle, width: parseFloat(style.outlineWidth) };
      });
      expect(outline.style).not.toBe("none");
      expect(outline.width).toBeGreaterThanOrEqual(2);
    }
  });

  test("the theme toggle works with Enter and Space", async ({ page }) => {
    await page.emulateMedia({ colorScheme: "light" });
    await page.goto("/");
    const toggle = page.getByRole("button", { name: /پوسته/ });
    const html = page.locator("html");

    await toggle.focus();
    await page.keyboard.press("Enter");
    await expect(html).toHaveAttribute("data-theme", "dark");
    await page.keyboard.press("Space");
    await expect(html).toHaveAttribute("data-theme", "light");
  });
});

test.describe("theme", () => {
  test("follows the system preference when nothing is stored", async ({ page }) => {
    for (const scheme of ["light", "dark"]) {
      await page.emulateMedia({ colorScheme: scheme });
      await page.goto("/");
      await expect(page.locator("html")).toHaveAttribute("data-theme", scheme);
    }
  });

  test("toggling updates state, label, storage, and survives a reload", async ({ page }) => {
    await page.emulateMedia({ colorScheme: "light" });
    await page.goto("/");
    const toggle = page.getByRole("button", { name: /پوسته/ });

    await expect(toggle).toHaveAttribute("aria-pressed", "false");
    await expect(toggle).toHaveAccessibleName("فعال‌کردن پوستهٔ تاریک");
    await toggle.click();

    await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
    await expect(toggle).toHaveAttribute("aria-pressed", "true");
    await expect(toggle).toHaveAccessibleName("فعال‌کردن پوستهٔ روشن");
    expect(await page.evaluate((key) => localStorage.getItem(key), THEME_KEY)).toBe("dark");

    await page.reload();
    await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  });

  test("a stored choice overrides the system preference", async ({ page }) => {
    await page.emulateMedia({ colorScheme: "dark" });
    await page.addInitScript((key) => localStorage.setItem(key, "light"), THEME_KEY);
    await page.goto("/");

    await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
  });

  test("still works when browser storage is unavailable", async ({ page }) => {
    await page.addInitScript(() => {
      Object.defineProperty(window, "localStorage", {
        get() {
          throw new Error("storage blocked");
        },
      });
    });
    await page.emulateMedia({ colorScheme: "light" });
    await page.goto("/");

    await page.getByRole("button", { name: /پوسته/ }).click();
    await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  });
});
