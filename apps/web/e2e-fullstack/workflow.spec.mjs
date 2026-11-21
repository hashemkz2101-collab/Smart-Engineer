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

  // Intake: save a step incomplete, reload, finish it, and see invalid input rejected.
  await page.getByRole("button", { name: /موقعیت/ }).click();
  await page.getByLabel("شهر (ضروری)").fill("تهران");
  await page.getByRole("button", { name: "ذخیرهٔ این مرحله" }).click();
  await expect(page.getByText(/برای تکمیل این مرحله لازم است: استان/)).toBeVisible();
  await page.reload();
  await page.getByRole("button", { name: /موقعیت/ }).click();
  await expect(page.getByLabel("شهر (ضروری)")).toHaveValue("تهران");
  await page.getByLabel("استان (ضروری)").fill("تهران");
  await page.getByLabel("عرض جغرافیایی").fill("95");
  await page.getByLabel("طول جغرافیایی").fill("51.4");
  await page.getByRole("button", { name: "ذخیرهٔ این مرحله" }).click();
  await expect(page.getByText("عدد خارج از محدودهٔ مجاز است.")).toBeVisible();
  await page.getByLabel("عرض جغرافیایی").fill("35.69");
  await page.getByRole("button", { name: "ذخیرهٔ این مرحله" }).click();
  await expect(page.getByText("ذخیره شد؛ این مرحله کامل است.")).toBeVisible();
  await page.reload();
  await page.getByRole("button", { name: /موقعیت/ }).click();
  await expect(page.getByLabel("عرض جغرافیایی")).toHaveValue("35.69");

  // Site data: an L-shaped parcel (75 m2) declared as 80 m2 reports the discrepancy.
  await page.getByLabel("شکل قطعه").selectOption("irregular");
  await page.getByLabel("مساحت اظهارشده (متر مربع)").fill("80");
  const vertices = [[0, 0], [10, 0], [10, 5], [5, 5], [5, 10], [0, 10]];
  const listLabel = "رئوس مرز (به ترتیب دور قطعه)";
  for (const [index, [x, y]] of vertices.entries()) {
    await page.getByRole("button", { name: `افزودن ردیف به ${listLabel}` }).click();
    await page.getByLabel(`${listLabel} ${index + 1}: X (ضروری)`).fill(String(x));
    await page.getByLabel(`${listLabel} ${index + 1}: Y (ضروری)`).fill(String(y));
  }
  await page.getByRole("button", { name: "ذخیرهٔ این بخش" }).click();
  await expect(page.getByText("ذخیره شد؛ این بخش کامل است.")).toBeVisible();
  const report = page.getByTestId("area-report");
  await expect(report).toHaveAttribute("data-status", "discrepancy");
  await expect(report).toContainText("75");
  await page.reload();
  await expect(page.getByLabel(`${listLabel} 6: Y (ضروری)`)).toHaveValue("10");
  await expect(page.getByTestId("area-report")).toHaveAttribute("data-status", "discrepancy");
  await page.getByRole("button", { name: /خاک/ }).click();
  await expect(page.getByTestId("soil-not-provided")).toContainText("ظرفیت باربری");

  // Zoning: a value without a source needs inquiry; adding a verified source verifies it.
  await page.getByRole("button", { name: /سطح اشغال/ }).click();
  await page.getByLabel("حداکثر سطح اشغال (درصد)").fill("60");
  await page.getByRole("button", { name: "ذخیرهٔ این ضابطه" }).click();
  await expect(page.getByText("ذخیره شد؛ وضعیت: نیازمند استعلام.")).toBeVisible();
  await page.reload();
  await page.getByRole("button", { name: /سطح اشغال/ }).click();
  await expect(page.getByTestId("zoning-status")).toHaveAttribute("data-status", "needs_inquiry");
  await page.getByLabel("تاریخ منبع").fill("1405-02-10");
  await page.getByRole("button", { name: "ذخیرهٔ این ضابطه" }).click();
  await expect(page.getByText("با تاریخ، تقویم آن را هم انتخاب کنید.")).toBeVisible();
  await page.getByLabel("تقویم تاریخ").selectOption("jalali");
  await page.getByLabel("نوع منبع").selectOption("municipality_letter");
  await page.getByLabel("عنوان منبع").fill("نامهٔ شهرداری");
  await page.getByLabel(/تأیید می‌کنم/).check();
  await page.getByRole("button", { name: "ذخیرهٔ این ضابطه" }).click();
  await expect(page.getByText("ذخیره شد؛ وضعیت: تأییدشده.")).toBeVisible();
  await page.reload();
  await page.getByRole("button", { name: /سطح اشغال/ }).click();
  await expect(page.getByTestId("zoning-status")).toHaveAttribute("data-status", "verified");
  await expect(page.getByLabel("تاریخ منبع")).toHaveValue("1405-02-10");

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
  await page.getByRole("button", { name: "افزودن", exact: true }).click();
  await expect(page.getByText("مهمان آزمایشی")).toBeVisible();
  await expect(page.getByText("عضوی به پروژه اضافه شد")).toBeVisible();

  // The guest now sees the project with the architect's limited permissions.
  await guest.goto("/projects");
  await guest.getByRole("link", { name: "ویلای ویرایش‌شده" }).click();
  await expect(guest.getByText(/نقش شما:\s*معمار/)).toBeVisible();
  await expect(guest.getByRole("button", { name: "بایگانی پروژه" })).toHaveCount(0);
  await expect(guest.getByRole("button", { name: "ذخیرهٔ تغییرات" })).toBeVisible();
  await expect(guest.getByRole("button", { name: "ذخیرهٔ این بخش" })).toBeVisible();
  await expect(guest.getByRole("button", { name: "ذخیرهٔ این ضابطه" })).toBeVisible();

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
