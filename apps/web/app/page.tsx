import Link from "next/link";

export default function HomePage() {
  return (
    <>
      <section className="page-heading" aria-labelledby="page-title">
        <p className="eyebrow">محیط کاری مهندسی</p>
        <h1 id="page-title">به Smart Engineer خوش آمدید</h1>
        <p className="page-description">
          بستری برای همراهی فرایندهای طراحی و هماهنگی مهندسی پروژه‌های ساختمانی،
          با تأکید بر شفافیت و قابلیت ردیابی.
        </p>
      </section>

      <section className="workspace-panel" aria-labelledby="workspace-title">
        <div className="panel-heading">
          <span className="panel-marker" aria-hidden="true">
            <svg viewBox="0 0 24 24" fill="none">
              <path
                d="M4.5 7.5h15M7.5 4.5v3m9-3v3M5.5 5.5h13a1 1 0 0 1 1 1v12a1 1 0 0 1-1 1h-13a1 1 0 0 1-1-1v-12a1 1 0 0 1 1-1Z"
                stroke="currentColor"
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth="1.5"
              />
              <path
                d="M8 11h3m-3 3h8m-8 3h5"
                stroke="currentColor"
                strokeLinecap="round"
                strokeWidth="1.5"
              />
            </svg>
          </span>
          <div>
            <h2 id="workspace-title">محیط کار</h2>
            <p className="panel-kicker">حساب، سازمان و مدیریت پروژه</p>
          </div>
        </div>
        <p className="panel-message">
          در این نسخه می‌توانید حساب بسازید، سازمان و اعضای آن را مدیریت کنید و
          پروژه‌ها را با نقش‌های مشخص ایجاد، ویرایش و بایگانی کنید. طراحی
          معماری، محاسبات مهندسی و برآورد هنوز پیاده‌سازی نشده‌اند.
        </p>
        <p className="cta-row">
          <Link className="button" href="/register">
            ایجاد حساب
          </Link>
          <Link className="button button-secondary" href="/login">
            ورود به حساب
          </Link>
        </p>
      </section>
    </>
  );
}
