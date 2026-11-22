import { expect, test } from "@playwright/test";

// Real browser -> real API -> real database: a project owner invites an outsider
// straight into a project; the invitee has nothing before accepting and exactly the
// invited role afterwards.
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

test("an outsider is invited to a project and gets only the invited role", async ({
  page,
  browser,
}) => {
  const guestEmail = `pguest-${run}@example.com`;
  await register(page, "مالک دعوت", `powner-${run}@example.com`);
  await page.getByLabel("نام پروژه").fill("پروژهٔ دعوت");
  await page.getByRole("button", { name: "ایجاد پروژه" }).click();
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("پروژهٔ دعوت");
  const projectUrl = page.url();

  const guestContext = await browser.newContext({ locale: "fa-IR" });
  const guest = await guestContext.newPage();
  await register(guest, "مهمان پروژه", guestEmail);

  await page.getByLabel("ایمیل فرد دعوت‌شده به پروژه").fill(guestEmail);
  await page.getByLabel("نقش فرد دعوت‌شده در پروژه").first().selectOption("quantity_surveyor");
  await page.getByRole("button", { name: "ساخت دعوت‌نامهٔ پروژه" }).click();
  const link = await page.locator("#project-invite-link").inputValue();
  await expect(page.getByRole("button", { name: `لغو دعوت ${guestEmail}` })).toBeVisible();
  await expect(page.getByText("دعوت‌نامهٔ پروژه ساخته شد")).toBeVisible();

  // Before accepting: no access at all.
  await guest.goto(projectUrl);
  await expect(guest.locator("#main-content").getByRole("alert")).toBeVisible();

  await guest.goto(new URL(link).pathname + new URL(link).search);
  await guest.getByRole("button", { name: "پذیرش دعوت" }).click();
  await expect(guest.getByText("دعوت پروژه پذیرفته شد.")).toBeVisible();
  await guest.getByRole("link", { name: "رفتن به پروژه" }).click();
  await expect(guest.getByText(/نقش شما:\s*متره‌گر/)).toBeVisible();
  // The quantity surveyor cannot manage members or invitations.
  await expect(guest.getByRole("button", { name: "ساخت دعوت‌نامهٔ پروژه" })).toHaveCount(0);

  await page.reload();
  await expect(page.getByText("دعوت پروژه پذیرفته شد")).toBeVisible();
  await expect(page.getByRole("button", { name: `لغو دعوت ${guestEmail}` })).toHaveCount(0);
  await guestContext.close();
});
