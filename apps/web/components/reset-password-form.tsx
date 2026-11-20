"use client";

import Link from "next/link";
import { useState, type FormEvent } from "react";

import { api, toApiError } from "../lib/api";
import { FormError, FormField, FormNotice } from "./form-field";

export function ResetPasswordForm({ token }: { token?: string }) {
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  if (!token) {
    return (
      <div className="form-panel">
        <p className="alert alert-error" role="alert">
          پیوند بازیابی ناقص است. دوباره درخواست بازیابی بدهید.
        </p>
        <Link href="/forgot-password">درخواست پیوند تازه</Link>
      </div>
    );
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api.post("/auth/password-reset/confirm", {
        token,
        new_password: password,
      });
      setDone("رمز عبور تغییر کرد. اکنون می‌توانید وارد شوید.");
    } catch (failure) {
      setError(toApiError(failure).userMessage);
      setBusy(false);
    }
  }

  return (
    <form className="form-panel" onSubmit={submit} noValidate>
      <FormField id="reset-password" label="رمز عبور تازه" hint="دست‌کم ۱۰ نویسه.">
        <input
          id="reset-password"
          type="password"
          dir="ltr"
          autoComplete="new-password"
          required
          aria-describedby="reset-password-hint"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
        />
      </FormField>
      <FormError message={error} />
      <FormNotice message={done} />
      {done ? (
        <Link className="button" href="/login">
          رفتن به ورود
        </Link>
      ) : (
        <button className="button" type="submit" disabled={busy}>
          تغییر رمز عبور
        </button>
      )}
    </form>
  );
}
