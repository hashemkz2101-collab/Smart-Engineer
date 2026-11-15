"use client";

export default function ErrorPage({
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <section className="error-panel" aria-labelledby="error-title">
      <p className="eyebrow">خطا</p>
      <h1 id="error-title">نمایش این صفحه ممکن نشد</h1>
      <p>لطفاً دوباره تلاش کنید. جزئیات داخلی خطا نمایش داده نمی‌شود.</p>
      <button className="retry-button" onClick={reset} type="button">
        تلاش دوباره
      </button>
    </section>
  );
}
