"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

import { api, toApiError } from "../lib/api";
import { useAuth } from "./auth-provider";
import { FormError, FormField } from "./form-field";

export function RegisterForm() {
  const { signIn } = useAuth();
  const router = useRouter();
  const [displayName, setDisplayName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api.post("/auth/register", {
        email,
        display_name: displayName,
        password,
      });
    } catch (failure) {
      setError(toApiError(failure).userMessage);
      setBusy(false);
      return;
    }
    try {
      await signIn(email, password);
      router.replace("/projects");
    } catch (failure) {
      // The account exists; only the automatic sign-in failed (for example when
      // email verification is required).
      setError(toApiError(failure).userMessage);
      setBusy(false);
    }
  }

  return (
    <form className="form-panel" onSubmit={submit} noValidate>
      <FormField id="register-name" label="نام و نام خانوادگی">
        <input
          id="register-name"
          type="text"
          autoComplete="name"
          required
          maxLength={200}
          value={displayName}
          onChange={(event) => setDisplayName(event.target.value)}
        />
      </FormField>
      <FormField id="register-email" label="ایمیل">
        <input
          id="register-email"
          type="email"
          dir="ltr"
          autoComplete="email"
          required
          value={email}
          onChange={(event) => setEmail(event.target.value)}
        />
      </FormField>
      <FormField
        id="register-password"
        label="رمز عبور"
        hint="دست‌کم ۱۰ نویسه. قاعدهٔ خاصی برای حروف و نمادها نیست؛ جملهٔ بلند و منحصربه‌فرد بهتر است."
      >
        <input
          id="register-password"
          type="password"
          dir="ltr"
          autoComplete="new-password"
          required
          aria-describedby="register-password-hint"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
        />
      </FormField>
      <FormError message={error} />
      <button className="button" type="submit" disabled={busy}>
        {busy ? "در حال ایجاد حساب…" : "ایجاد حساب"}
      </button>
      <p className="form-links">
        <Link href="/login">حساب دارید؟ وارد شوید</Link>
      </p>
    </form>
  );
}
