import assert from "node:assert/strict";
import test from "node:test";

const baseUrl = process.env.SMART_ENGINEER_WEB_URL ?? "http://127.0.0.1:3000";

async function getHomePage() {
  const response = await fetch(baseUrl);
  assert.equal(response.status, 200, `Home route at ${baseUrl} must respond with HTTP 200`);
  assert.match(response.headers.get("content-type") ?? "", /text\/html/);
  return response.text();
}

test("home route renders the Persian RTL application shell", async () => {
  const html = await getHomePage();

  assert.match(html, /<html\b[^>]*\blang="fa-IR"/);
  assert.match(html, /<html\b[^>]*\bdir="rtl"/);
  assert.match(html, /<main\b[^>]*id="main-content"/);
  assert.match(html, /<h1\b[^>]*>به Smart Engineer خوش آمدید<\/h1>/);
});

test("home page contains accessible navigation and theme controls", async () => {
  const html = await getHomePage();

  assert.match(html, /<a\b[^>]*class="skip-link"[^>]*href="#main-content"/);
  assert.match(html, /<nav\b[^>]*aria-label="ناوبری اصلی"/);
  assert.match(html, /<a\b[^>]*href="\/"[^>]*>نمای کلی<\/a>/);
  assert.match(html, /<button\b[^>]*aria-label="تغییر پوسته"/);
  assert.match(html, /localStorage\.getItem\("smart-engineer-theme"\)/);
  assert.match(html, /matchMedia\("\(prefers-color-scheme: dark\)"\)/);
});

test("home page identifies the shell without claiming unfinished features", async () => {
  const html = await getHomePage();

  assert.match(html, /پوستهٔ پایهٔ برنامه آماده است/);
  assert.match(html, /هنوز در این نسخه پیاده‌سازی نشده‌اند/);
});

test("unknown routes render a Persian not-found page with a home link", async () => {
  const response = await fetch(`${baseUrl}/p0-04-not-found-check`);
  const html = await response.text();

  assert.equal(response.status, 404);
  assert.match(html, /این نشانی در دسترس نیست/);
  assert.match(html, /href="\/"[^>]*>بازگشت به صفحهٔ اصلی<\/a>/);
});
