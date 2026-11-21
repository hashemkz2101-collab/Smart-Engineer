import { expect, test } from "@playwright/test";

// Real browser -> real Next.js -> real FastAPI -> real database. Unique emails keep
// repeated runs independent of earlier data.
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

test("owner and guest complete the account, project and invitation workflow", async ({
  page,
  browser,
}) => {
  const ownerEmail = `owner-${run}@example.com`;
  const guestEmail = `guest-${run}@example.com`;

  // Owner signs up, creates a project and edits it.
  await register(page, "مالک آزمایشی", ownerEmail);
  await page.getByLabel("نام پروژه").fill("ویلای آزمایشی");
  await page.getByRole("button", { name: "ایجاد پروژه" }).click();
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("ویلای آزمایشی");
  const projectUrl = page.url();

  await page.getByLabel("نام پروژه").fill("ویلای ویرایش‌شده");
  await page.getByRole("button", { name: "ذخیرهٔ تغییرات" }).click();
  await expect(page.getByText("تغییرات ذخیره شد.")).toBeVisible();
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("ویلای ویرایش‌شده");
  await expect(page.getByText("مشخصات پروژه ویرایش شد")).toBeVisible();

  // Archive and restore.
  await page.getByRole("button", { name: "بایگانی پروژه" }).click();
  await expect(page.getByText("این پروژه بایگانی شده و فقط‌خواندنی است.")).toBeVisible();
  await expect(page.getByRole("button", { name: "ذخیرهٔ تغییرات" })).toHaveCount(0);
  await page.getByRole("button", { name: "بازگردانی از بایگانی" }).click();
  await expect(page.getByText("این پروژه بایگانی شده و فقط‌خواندنی است.")).toHaveCount(0);

  // A second person, in a separate browser context, cannot see the project yet.
  const guestContext = await browser.newContext({ locale: "fa-IR" });
  const guest = await guestContext.newPage();
  await register(guest, "مهمان آزمایشی", guestEmail);
  await guest.goto(projectUrl);
  await expect(guest.locator("#main-content").getByRole("alert")).toHaveText(
    "مورد درخواستی پیدا نشد.",
  );

  // Owner invites the guest; the guest accepts with the one-time link.
  await page.goto("/organization");
  await page.getByLabel("ایمیل فرد دعوت‌شده").fill(guestEmail);
  await page.getByRole("button", { name: "ساخت دعوت‌نامه" }).click();
  const inviteLink = await page.locator("#invite-link").inputValue();
  expect(inviteLink).toContain("/invitations/accept?token=");

  await guest.goto(new URL(inviteLink).pathname + new URL(inviteLink).search);
  await guest.getByRole("button", { name: "پذیرش دعوت" }).click();
  await expect(guest.getByText(/به سازمان پیوستید/)).toBeVisible();
  // The token is single-use.
  await guest.reload();
  await guest.getByRole("button", { name: "پذیرش دعوت" }).click();
  await expect(guest.locator("#main-content").getByRole("alert")).toContainText(
    "نامعتبر است یا منقضی شده است",
  );

  // Owner gives the guest the architect role on the project.
  await page.goto(projectUrl);
  await page.getByLabel("ایمیل عضو").fill(guestEmail);
  await page.locator("#member-role").selectOption("architect");
  await page.getByRole("button", { name: "افزودن" }).click();
  await expect(page.getByText("مهمان آزمایشی")).toBeVisible();
  await expect(page.getByText("عضوی به پروژه اضافه شد")).toBeVisible();

  // The guest now sees the project with the architect's limited permissions.
  await guest.goto("/projects");
  await guest.getByRole("link", { name: "ویلای ویرایش‌شده" }).click();
  await expect(guest.getByText(/نقش شما:\s*معمار/)).toBeVisible();
  await expect(guest.getByRole("button", { name: "بایگانی پروژه" })).toHaveCount(0);
  await expect(guest.getByRole("button", { name: "ذخیرهٔ تغییرات" })).toBeVisible();

  await guestContext.close();
});

test("signing out ends the session and protected pages redirect to login", async ({ page }) => {
  await register(page, "کاربر خروج", `logout-${run}@example.com`);
  await page.getByRole("button", { name: "خروج" }).click();
  await expect(page).toHaveURL(/\/$/);

  await page.goto("/projects");
  await expect(page).toHaveURL(/\/login\?next=%2Fprojects$/);
});

test("wrong passwords are rejected and repeated failures lock the account", async ({ page }) => {
  const email = `lock-${run}@example.com`;
  await register(page, "کاربر قفل", email);
  await page.getByRole("button", { name: "خروج" }).click();

  await page.goto("/login");
  for (let attempt = 0; attempt < 5; attempt += 1) {
    await page.getByLabel("ایمیل").fill(email);
    await page.getByLabel("رمز عبور").fill("wrong password!");
    await page.getByRole("button", { name: "ورود", exact: true }).click();
    await expect(page.locator("#main-content").getByRole("alert")).toHaveText(
      "ایمیل یا رمز عبور درست نیست.",
    );
  }
  await page.getByLabel("رمز عبور").fill(PASSWORD);
  await page.getByRole("button", { name: "ورود", exact: true }).click();
  await expect(page.locator("#main-content").getByRole("alert")).toContainText(
    "تلاش‌های ناموفق زیاد بود",
  );
});
