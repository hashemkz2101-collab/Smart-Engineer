"use client";

import Link from "next/link";
import { useState, type FormEvent } from "react";

import { api, toApiError } from "../lib/api";
import { FormError, FormField, FormNotice } from "./form-field";

export function ForgotPasswordForm() {
  const [email, setEmail] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      await api.post("/auth/password-reset/request", { email });
      // The same message is shown whether or not the email has an account.
      setNotice(
        "اگر حسابی با این ایمیل وجود داشته باشد، پیوند بازیابی برای آن ارسال می‌شود.",
      );
    } catch (failure) {
      setError(toApiError(failure).userMessage);
    }
    setBusy(false);
  }

  return (
    <form className="form-panel" onSubmit={submit} noValidate>
      <p className="field-hint">
        ارسال ایمیل بازیابی هنوز در این نسخه فعال نیست؛ تا فعال‌شدن آن، برای
        بازیابی رمز با مدیر سامانه تماس بگیرید.
      </p>
      <FormField id="forgot-email" label="ایمیل">
        <input
          id="forgot-email"
          type="email"
          dir="ltr"
          autoComplete="email"
          required
          value={email}
          onChange={(event) => setEmail(event.target.value)}
        />
      </FormField>
      <FormError message={error} />
      <FormNotice message={notice} />
      <button className="button" type="submit" disabled={busy}>
        درخواست پیوند بازیابی
      </button>
      <p className="form-links">
        <Link href="/login">بازگشت به ورود</Link>
      </p>
    </form>
  );
}
