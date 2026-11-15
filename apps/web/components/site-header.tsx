import Link from "next/link";

import { ThemeToggle } from "./theme-toggle";

export function SiteHeader() {
  return (
    <header className="site-header">
      <div className="header-inner">
        <Link className="brand" href="/" aria-label="Smart Engineer، صفحهٔ اصلی">
          <span className="brand-mark" aria-hidden="true">
            SE
          </span>
          <span className="brand-name">Smart Engineer</span>
        </Link>
        <div className="header-actions">
          <nav className="primary-nav" aria-label="ناوبری اصلی">
            <Link aria-current="page" href="/">
              نمای کلی
            </Link>
          </nav>
          <ThemeToggle />
        </div>
      </div>
    </header>
  );
}
