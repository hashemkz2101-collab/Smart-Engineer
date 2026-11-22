"use client";

import { useState, type FormEvent } from "react";

import { api, toApiError } from "../lib/api";
import { formatDate } from "../lib/messages";
import { useResource } from "../lib/use-resource";
import { FormField } from "./form-field";

type ProjectFile = {
  id: string;
  original_name: string;
  kind: string;
  document_date: string | null;
  ownership: string | null;
  detected_type: string;
  size_bytes: number;
  scan_status: "pending" | "clean" | "quarantined";
  scan_detail: string | null;
  uploaded_by_name: string | null;
  created_at: string | null;
  downloadable: boolean;
};

const kindLabels: Record<string, string> = {
  survey: "نقشهٔ برداری",
  deed: "سند مالکیت",
  zoning_letter: "نامهٔ ضوابط",
  geotechnical_report: "گزارش ژئوتکنیک",
  site_photo: "عکس زمین",
  reference_image: "تصویر مرجع",
  other: "سایر",
};

const scanLabels: Record<string, string> = {
  clean: "بررسی شد",
  pending: "در انتظار اسکن",
  quarantined: "قرنطینه",
};

function formatSize(bytes: number): string {
  return bytes >= 1024 * 1024
    ? `${(bytes / (1024 * 1024)).toFixed(1)} مگابایت`
    : `${Math.max(1, Math.round(bytes / 1024))} کیلوبایت`;
}

export function FilesPanel({
  projectId,
  canUpload,
  canDelete,
  version,
}: {
  projectId: string;
  canUpload: boolean;
  canDelete: boolean;
  version: number;
}) {
  const [reload, setReload] = useState(0);
  const [file, setFile] = useState<File | null>(null);
  const [kind, setKind] = useState("");
  const [documentDate, setDocumentDate] = useState("");
  const [ownership, setOwnership] = useState("");
  const [inputKey, setInputKey] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const files = useResource<{ files: ProjectFile[] }>(
    `/projects/${projectId}/files`,
    version + reload,
  );

  async function upload(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setNotice(null);
    if (!file) {
      setError("یک فایل انتخاب کنید.");
      return;
    }
    if (!kind) {
      setError("نوع سند را انتخاب کنید.");
      return;
    }
    setBusy(true);
    const query = new URLSearchParams({ filename: file.name, kind });
    if (documentDate) query.set("document_date", documentDate);
    if (ownership.trim()) query.set("ownership", ownership.trim());
    try {
      const saved = await api.upload<ProjectFile>(`/projects/${projectId}/files?${query}`, file);
      setNotice(
        saved.scan_status === "quarantined"
          ? "فایل ذخیره شد اما به‌دلیل نتیجهٔ اسکن در قرنطینه است و قابل دانلود نیست."
          : saved.scan_status === "pending"
            ? "فایل ذخیره شد و پس از اسکن قابل دانلود می‌شود."
            : "فایل بارگذاری شد.",
      );
      setFile(null);
      setKind("");
      setDocumentDate("");
      setOwnership("");
      setInputKey((current) => current + 1);
      setReload((current) => current + 1);
    } catch (failure) {
      setError(toApiError(failure).userMessage);
    }
    setBusy(false);
  }

  async function remove(item: ProjectFile) {
    setError(null);
    setNotice(null);
    try {
      await api.delete<void>(`/projects/${projectId}/files/${item.id}`);
      setNotice("فایل حذف شد.");
      setReload((current) => current + 1);
    } catch (failure) {
      setError(toApiError(failure).userMessage);
    }
  }

  return (
    <section className="detail-section" aria-labelledby="files-title">
      <h2 id="files-title">فایل‌ها و مدارک</h2>
      <p className="field-hint">
        فقط PDF، PNG، JPEG و WebP تا ۱۰ مگابایت. فایل‌ها خصوصی نگه داشته می‌شوند و فقط اعضای
        پروژه می‌توانند دانلودشان کنند.
      </p>
      {files.error ? (
        <p className="alert alert-error" role="alert">
          {files.error.userMessage}
        </p>
      ) : null}
      {canUpload ? (
        <form className="form-panel" onSubmit={upload} noValidate aria-label="بارگذاری فایل">
          <FormField id="file-input" label="فایل">
            <input
              key={inputKey}
              id="file-input"
              type="file"
              accept=".pdf,.png,.jpg,.jpeg,.webp"
              onChange={(event) => setFile(event.target.files?.[0] ?? null)}
            />
          </FormField>
          <FormField id="file-kind" label="نوع سند">
            <select id="file-kind" value={kind} onChange={(event) => setKind(event.target.value)}>
              <option value="">انتخاب نشده</option>
              {Object.entries(kindLabels).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </FormField>
          <FormField
            id="file-date"
            label="تاریخ سند"
            hint="اختیاری؛ به شکل میلادی سال-ماه-روز، مثل 2026-05-01."
          >
            <input
              id="file-date"
              type="text"
              dir="ltr"
              value={documentDate}
              onChange={(event) => setDocumentDate(event.target.value)}
            />
          </FormField>
          <FormField id="file-ownership" label="مالک سند" hint="اختیاری؛ مثلاً کارفرما یا شهرداری.">
            <input
              id="file-ownership"
              type="text"
              value={ownership}
              onChange={(event) => setOwnership(event.target.value)}
            />
          </FormField>
          <button className="button" type="submit" disabled={busy}>
            {busy ? "در حال بارگذاری…" : "بارگذاری فایل"}
          </button>
        </form>
      ) : null}
      {error ? (
        <div role="alert" className="alert alert-error">
          {error}
        </div>
      ) : null}
      {notice ? (
        <div role="status" className="alert alert-success">
          {notice}
        </div>
      ) : null}
      {files.data && files.data.files.length === 0 ? (
        <p className="field-hint">هنوز فایلی بارگذاری نشده است.</p>
      ) : null}
      {files.data && files.data.files.length > 0 ? (
        <ul className="file-list" aria-label="فهرست فایل‌ها">
          {files.data.files.map((item) => (
            <li className="file-item" key={item.id} data-scan={item.scan_status}>
              <strong dir="auto">{item.original_name}</strong>
              <span className="field-hint">
                {kindLabels[item.kind] ?? item.kind} · {formatSize(item.size_bytes)} ·{" "}
                {scanLabels[item.scan_status]}
                {item.document_date ? ` · تاریخ سند ${item.document_date}` : ""}
                {item.ownership ? ` · مالک: ${item.ownership}` : ""}
                {item.uploaded_by_name ? ` · بارگذار: ${item.uploaded_by_name}` : ""}
                {item.created_at ? ` · ${formatDate(item.created_at)}` : ""}
              </span>
              {item.downloadable ? (
                <a
                  className="button button-secondary"
                  href={`/api/v1/projects/${projectId}/files/${item.id}/download`}
                  download
                >
                  دانلود {item.original_name}
                </a>
              ) : (
                <span className="field-hint">قابل دانلود نیست</span>
              )}
              {canDelete ? (
                <button
                  type="button"
                  className="button button-secondary"
                  onClick={() => void remove(item)}
                >
                  حذف {item.original_name}
                </button>
              ) : null}
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}
