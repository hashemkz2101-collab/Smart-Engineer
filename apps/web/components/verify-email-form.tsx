"use client";

import Link from "next/link";
import { useState } from "react";

import { api, toApiError } from "../lib/api";
import { FormError } from "./form-field";

// Confirmation needs an explicit click: mail scanners that open links must not be
// able to use up the one-time token.
export function VerifyEmailForm({ token }: { token?: string }) {
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);
  const [busy, setBusy] = useState(false);

  if (!token) {
    return (
      <div className="form-panel">
        <p className="alert alert-error" role="alert">
          پیوند تأیید ناقص است. از صفحهٔ ورود، ارسال دوبارهٔ ایمیل تأیید را بزنید.
        </p>
        <Link href="/login">رفتن به ورود</Link>
      </div>
    );
  }

  if (done) {
    return (
      <div className="form-panel">
        <p className="alert alert-success" role="status">
          ایمیل شما تأیید شد. اکنون می‌توانید وارد شوید.
        </p>
        <Link className="button" href="/login">
          رفتن به ورود
        </Link>
      </div>
    );
  }

  async function confirm() {
    setBusy(true);
    setError(null);
    try {
      await api.post("/auth/email-verification/confirm", { token });
      setDone(true);
    } catch (failure) {
      setError(toApiError(failure).userMessage);
      setBusy(false);
    }
  }

  return (
    <div className="form-panel">
      <p>برای تکمیل ثبت‌نام، تأیید نشانی ایمیل را بزنید.</p>
      <FormError message={error} />
      <button className="button" type="button" disabled={busy} onClick={confirm}>
        تأیید ایمیل
      </button>
      <p className="form-links">
        <Link href="/login">بازگشت به ورود</Link>
      </p>
    </div>
  );
}
