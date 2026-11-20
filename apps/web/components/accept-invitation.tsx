"use client";

import Link from "next/link";
import { useState } from "react";

import { api, toApiError } from "../lib/api";
import { orgRoleLabels } from "../lib/messages";
import { FormError } from "./form-field";

export function AcceptInvitation({ token }: { token?: string }) {
  const [error, setError] = useState<string | null>(null);
  const [joinedRole, setJoinedRole] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  if (!token) {
    return (
      <p className="alert alert-error" role="alert">
        پیوند دعوت ناقص است. از فرد دعوت‌کننده پیوند تازه بخواهید.
      </p>
    );
  }

  async function accept() {
    setBusy(true);
    setError(null);
    try {
      const result = await api.post<{ org_role: string }>("/invitations/accept", { token });
      setJoinedRole(result.org_role);
    } catch (failure) {
      setError(toApiError(failure).userMessage);
      setBusy(false);
    }
  }

  if (joinedRole) {
    return (
      <div className="form-panel">
        <p className="alert alert-success" role="status">
          به سازمان پیوستید (نقش: {orgRoleLabels[joinedRole] ?? joinedRole}).
        </p>
        <Link className="button" href="/organization">
          رفتن به سازمان
        </Link>
      </div>
    );
  }

  return (
    <div className="form-panel">
      <p>
        برای پیوستن به سازمان، باید با همان ایمیلی وارد شده باشید که دعوت برای آن
        ساخته شده است.
      </p>
      <FormError message={error} />
      <button className="button" type="button" onClick={accept} disabled={busy}>
        پذیرش دعوت
      </button>
    </div>
  );
}
