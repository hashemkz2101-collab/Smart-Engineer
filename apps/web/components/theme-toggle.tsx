"use client";

import { useEffect, useState } from "react";

type Theme = "light" | "dark";

const storageKey = "smart-engineer-theme";

function systemTheme(): Theme {
  return window.matchMedia("(prefers-color-scheme: dark)").matches
    ? "dark"
    : "light";
}

export function ThemeToggle() {
  const [theme, setTheme] = useState<Theme | null>(null);

  useEffect(() => {
    const currentTheme =
      document.documentElement.dataset.theme === "dark" ? "dark" : systemTheme();
    setTheme(currentTheme);
  }, []);

  function toggleTheme() {
    const currentTheme =
      theme ??
      (document.documentElement.dataset.theme === "dark" ? "dark" : systemTheme());
    const nextTheme = currentTheme === "dark" ? "light" : "dark";

    document.documentElement.dataset.theme = nextTheme;
    setTheme(nextTheme);

    try {
      localStorage.setItem(storageKey, nextTheme);
    } catch {
      // The current page theme still changes when storage is unavailable.
    }
  }

  const accessibleLabel =
    theme === null
      ? "تغییر پوسته"
      : theme === "dark"
        ? "فعال‌کردن پوستهٔ روشن"
        : "فعال‌کردن پوستهٔ تاریک";

  return (
    <button
      aria-label={accessibleLabel}
      aria-pressed={theme === "dark"}
      className="theme-toggle"
      onClick={toggleTheme}
      type="button"
    >
      <svg
        aria-hidden="true"
        className="theme-icon"
        fill="none"
        viewBox="0 0 24 24"
      >
        {theme === "dark" ? (
          <path
            d="M20.2 15.3A8.4 8.4 0 0 1 8.7 3.8 8.5 8.5 0 1 0 20.2 15.3Z"
            stroke="currentColor"
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth="1.7"
          />
        ) : (
          <>
            <circle cx="12" cy="12" r="3.6" stroke="currentColor" strokeWidth="1.7" />
            <path
              d="M12 2.8v2m0 14.4v2m9.2-9.2h-2M4.8 12h-2m15.7-6.5-1.4 1.4M6.9 17.1l-1.4 1.4m13 0-1.4-1.4M6.9 6.9 5.5 5.5"
              stroke="currentColor"
              strokeLinecap="round"
              strokeWidth="1.7"
            />
          </>
        )}
      </svg>
      <span className="theme-toggle-label">پوسته</span>
    </button>
  );
}
