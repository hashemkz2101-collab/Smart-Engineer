"use client";

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

  if (state.status !== "authenticated") {
    return (
      <p className="status-text" role="status">
        در حال بررسی ورود…
      </p>
    );
  }
  return <>{children}</>;
}
