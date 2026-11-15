import Link from "next/link";

export default function NotFound() {
  return (
    <section className="not-found-panel" aria-labelledby="not-found-title">
      <p className="eyebrow">صفحه پیدا نشد</p>
      <h1 id="not-found-title">این نشانی در دسترس نیست</h1>
      <p>نشانی را بررسی کنید یا به صفحهٔ اصلی برگردید.</p>
      <Link className="home-link" href="/">
        بازگشت به صفحهٔ اصلی
      </Link>
    </section>
  );
}
