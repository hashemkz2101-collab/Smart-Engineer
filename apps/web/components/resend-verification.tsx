"use client";

import { useState } from "react";

import { api, toApiError } from "../lib/api";
import { FormError, FormNotice } from "./form-field";

// The same neutral message is shown whether or not the address has an account.
export function ResendVerification({ email }: { email: string }) {
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function resend() {
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      await api.post("/auth/email-verification/request", { email });
      setNotice("اگر این ایمیل تأییدنشده باشد، پیوند تأیید دوباره برایش ارسال می‌شود.");
    } catch (failure) {
      setError(toApiError(failure).userMessage);
    }
    setBusy(false);
  }

  return (
    <div>
      <button className="button button-secondary" type="button" disabled={busy} onClick={resend}>
        ارسال دوباره ایمیل تأیید
      </button>
      <FormError message={error} />
      <FormNotice message={notice} />
    </div>
  );
}
