"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

import { toApiError } from "../lib/api";
import { useAuth } from "./auth-provider";
import { FormError, FormField } from "./form-field";

// Only same-site paths are accepted, so a crafted link cannot send people elsewhere.
function safeNext(next: string | undefined): string {
  return next && next.startsWith("/") && !next.startsWith("//") ? next : "/projects";
}

export function LoginForm({ next }: { next?: string }) {
  const { signIn } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await signIn(email, password);
      router.replace(safeNext(next));
    } catch (failure) {
      setError(toApiError(failure).userMessage);
      setBusy(false);
    }
  }

  return (
    <form className="form-panel" onSubmit={submit} noValidate>
      <FormField id="login-email" label="ایمیل">
        <input
          id="login-email"
          type="email"
          dir="ltr"
          autoComplete="email"
          required
          value={email}
          onChange={(event) => setEmail(event.target.value)}
        />
      </FormField>
      <FormField id="login-password" label="رمز عبور">
        <input
          id="login-password"
          type="password"
          dir="ltr"
          autoComplete="current-password"
          required
          value={password}
          onChange={(event) => setPassword(event.target.value)}
        />
      </FormField>
      <FormError message={error} />
      <button className="button" type="submit" disabled={busy}>
        {busy ? "در حال ورود…" : "ورود"}
      </button>
      <p className="form-links">
        <Link href="/forgot-password">رمز عبور را فراموش کرده‌اید؟</Link>
        <Link href="/register">حساب ندارید؟ ثبت‌نام کنید</Link>
      </p>
    </form>
  );
}
