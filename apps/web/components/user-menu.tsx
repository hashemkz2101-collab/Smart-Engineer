"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";

import { useAuth } from "./auth-provider";

export function UserMenu() {
  const { state, signOut } = useAuth();
  const router = useRouter();

  if (state.status === "loading") {
    return null;
  }

  if (state.status === "anonymous") {
    return (
      <nav className="user-menu" aria-label="حساب کاربری">
        <Link href="/login">ورود</Link>
        <Link href="/register">ثبت‌نام</Link>
      </nav>
    );
  }

  return (
    <nav className="user-menu" aria-label="حساب کاربری">
      <Link href="/projects">پروژه‌ها</Link>
      <Link href="/organization">سازمان</Link>
      <span className="user-name">{state.user.display_name}</span>
      <button
        className="link-button"
        type="button"
        onClick={async () => {
          await signOut();
          router.push("/");
        }}
      >
        خروج
      </button>
    </nav>
  );
}
