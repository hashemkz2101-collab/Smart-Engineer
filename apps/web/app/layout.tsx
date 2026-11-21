import type { Metadata } from "next";
import type { ReactNode } from "react";

import { AuthProvider } from "../components/auth-provider";
import { SiteHeader } from "../components/site-header";
import "./globals.css";

export const metadata: Metadata = {
  title: "Smart Engineer",
  description: "محیط پایهٔ پلتفرم مهندسی هوشمند",
};

const themeBootstrap = `(() => {
  let theme;
  try {
    const savedTheme = localStorage.getItem("smart-engineer-theme");
    if (savedTheme === "light" || savedTheme === "dark") {
      theme = savedTheme;
    }
  } catch {
    // Storage can be unavailable; fall back to the operating-system preference.
  }
  if (!theme) {
    theme = window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }
  document.documentElement.dataset.theme = theme;
})();`;

export default function RootLayout({
  children,
}: Readonly<{
  children: ReactNode;
}>) {
  return (
    <html lang="fa-IR" dir="rtl" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeBootstrap }} />
      </head>
      <body>
        <a className="skip-link" href="#main-content">
          رفتن به محتوای اصلی
        </a>
        <AuthProvider>
          <SiteHeader />
          <main className="main-content" id="main-content" tabIndex={-1}>
            {children}
          </main>
        </AuthProvider>
        <footer className="site-footer">
          <div className="footer-inner">
            <p>محیط پایهٔ Smart Engineer</p>
          </div>
        </footer>
      </body>
    </html>
  );
}
