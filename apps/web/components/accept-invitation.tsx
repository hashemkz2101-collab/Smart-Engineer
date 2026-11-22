"use client";

import Link from "next/link";
import { useState } from "react";

import { api, toApiError } from "../lib/api";
import { orgRoleLabels } from "../lib/messages";
import { FormError } from "./form-field";

export function AcceptInvitation({ token }: { token?: string }) {
  const [error, setError] = useState<string | null>(null);
  const [joined, setJoined] = useState<{ role: string; projectId: string | null } | null>(null);
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
      const result = await api.post<{ org_role: string; project_id: string | null }>(
        "/invitations/accept",
        { token },
      );
      setJoined({ role: result.org_role, projectId: result.project_id });
    } catch (failure) {
      setError(toApiError(failure).userMessage);
      setBusy(false);
    }
  }

  if (joined) {
    return (
      <div className="form-panel">
        <p className="alert alert-success" role="status">
          {joined.projectId
            ? "دعوت پروژه پذیرفته شد."
            : `به سازمان پیوستید (نقش: ${orgRoleLabels[joined.role] ?? joined.role}).`}
        </p>
        <Link className="button" href={joined.projectId ? `/projects/${joined.projectId}` : "/organization"}>
          {joined.projectId ? "رفتن به پروژه" : "رفتن به سازمان"}
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
