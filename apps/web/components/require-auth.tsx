"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, type ReactNode } from "react";

import { useAuth } from "./auth-provider";

export function RequireAuth({ children }: { children: ReactNode }) {
  const { state } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (state.status === "anonymous") {
      const next = window.location.pathname + window.location.search;
      router.replace(`/login?next=${encodeURIComponent(next)}`);
    }
  }, [state.status, router]);

  if (state.status === "signed_out") {
    return (
      <p className="status-text" role="status">
        از حساب خارج شدید. <Link href="/">بازگشت به صفحهٔ اصلی</Link>
      </p>
    );
  }
  if (state.status !== "authenticated") {
    return (
      <p className="status-text" role="status">
        در حال بررسی ورود…
      </p>
    );
  }
  return <>{children}</>;
}
