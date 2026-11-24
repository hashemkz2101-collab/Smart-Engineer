"use client";

import { useState, type FormEvent } from "react";

import { api, toApiError } from "../lib/api";
import { formatDate } from "../lib/messages";
import { useResource } from "../lib/use-resource";
import { FormField } from "./form-field";

type ProjectFile = {
  id: string;
  series_id: string;
  version_number: number;
  is_latest: boolean;
  is_basis: boolean;
  basis_outdated: boolean;
  original_name: string;
  kind: string;
  document_date: string | null;
  ownership: string | null;
  detected_type: string;
  size_bytes: number;
  sha256: string;
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
  canSetBasis,
  version,
}: {
  projectId: string;
  canUpload: boolean;
  canDelete: boolean;
  canSetBasis: boolean;
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
  const [newVersionOf, setNewVersionOf] = useState("");
  const [comparison, setComparison] = useState<{ id: string; text: string } | null>(null);
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
    if (newVersionOf) query.set("new_version_of", newVersionOf);
    try {
      const saved = await api.upload<ProjectFile>(`/projects/${projectId}/files?${query}`, file);
      setNotice(
        saved.scan_status === "quarantined"
          ? "فایل ذخیره شد اما به‌دلیل نتیجهٔ اسکن در قرنطینه است و قابل دانلود نیست."
          : saved.scan_status === "pending"
            ? "فایل ذخیره شد و پس از اسکن قابل دانلود می‌شود."
            : newVersionOf
              ? `نسخهٔ ${saved.version_number} ثبت شد؛ نسخه‌های قبلی نگه داشته شد.`
              : "فایل بارگذاری شد.",
      );
      setFile(null);
      setKind("");
      setDocumentDate("");
      setOwnership("");
      setNewVersionOf("");
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

  async function restore(item: ProjectFile) {
    setError(null);
    setNotice(null);
    try {
      const saved = await api.post<ProjectFile>(
        `/projects/${projectId}/files/${item.id}/restore`,
        {},
      );
      setNotice(`نسخهٔ ${item.version_number} به‌عنوان نسخهٔ ${saved.version_number} بازیابی شد.`);
      setReload((current) => current + 1);
    } catch (failure) {
      setError(toApiError(failure).userMessage);
    }
  }

  async function toggleBasis(item: ProjectFile) {
    setError(null);
    setNotice(null);
    try {
      await api.put<ProjectFile>(`/projects/${projectId}/files/${item.id}/basis`, {
        is_basis: !item.is_basis,
      });
      setNotice(item.is_basis ? "علامت مبنای متره برداشته شد." : "به‌عنوان مبنای متره ثبت شد.");
      setReload((current) => current + 1);
    } catch (failure) {
      setError(toApiError(failure).userMessage);
    }
  }

  async function compare(item: ProjectFile, latest: ProjectFile) {
    setError(null);
    try {
      const result = await api.get<{
        identical_content: boolean;
        size_delta_bytes: number;
        type_changed: boolean;
      }>(`/projects/${projectId}/files/${item.id}/compare/${latest.id}`);
      const parts = [
        result.identical_content ? "محتوا یکسان است" : "محتوا تغییر کرده است",
        result.size_delta_bytes === 0
          ? "حجم بدون تغییر"
          : `تغییر حجم: ${result.size_delta_bytes > 0 ? "+" : "-"}${formatSize(Math.abs(result.size_delta_bytes))}`,
      ];
      if (result.type_changed) parts.push("نوع فایل تغییر کرده است");
      setComparison({
        id: item.id,
        text: `نسخهٔ ${item.version_number} در برابر نسخهٔ ${latest.version_number}: ${parts.join("؛ ")}`,
      });
    } catch (failure) {
      setError(toApiError(failure).userMessage);
    }
  }

  const latestOf = (item: ProjectFile) =>
    files.data?.files.find((other) => other.series_id === item.series_id && other.is_latest);

  return (
    <section className="detail-section" aria-labelledby="files-title">
      <h2 id="files-title">فایل‌ها و مدارک</h2>
      <p className="field-hint">
        نقشه و مدرک: PDF، DXF، DWG، IFC، Excel (XLSX، XLS، CSV)، Word (DOCX، DOC) و تصویر (PNG، JPEG، WebP) تا ۲۵ تا ۵۰ مگابایت بسته به نوع. فایل‌های دارای ماکرو (DOCM، XLSM) پذیرفته نمی‌شوند. فایل‌ها خصوصی نگه داشته می‌شوند و فقط اعضای
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
              accept=".pdf,.png,.jpg,.jpeg,.webp,.dxf,.dwg,.ifc,.xlsx,.xls,.csv,.docx,.doc"
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
          <FormField
            id="file-new-version"
            label="نسخهٔ جدید از فایل"
            hint="اختیاری؛ برای جایگزینی بدون حذف نسخهٔ قبلی."
          >
            <select
              id="file-new-version"
              value={newVersionOf}
              onChange={(event) => setNewVersionOf(event.target.value)}
            >
              <option value="">فایل تازه (نه نسخهٔ جدید)</option>
              {files.data?.files
                .filter((item) => item.is_latest)
                .map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.original_name} (نسخهٔ {item.version_number})
                  </option>
                ))}
            </select>
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
                نسخهٔ {item.version_number}
                {item.is_latest ? " (آخرین)" : ""}
                {item.is_basis ? " · مبنای متره و برآورد" : ""}
              </span>
              {item.basis_outdated ? (
                <span className="alert alert-error" role="status">
                  نسخهٔ جدیدتری از این فایل آمده است؛ محاسبات متره بر پایهٔ نسخهٔ قبلی‌اند و باید
                  بازبینی شوند.
                </span>
              ) : null}
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
              {canUpload && !item.is_latest && item.downloadable ? (
                <button
                  type="button"
                  className="button button-secondary"
                  onClick={() => void restore(item)}
                >
                  بازیابی نسخهٔ {item.version_number} از {item.original_name}
                </button>
              ) : null}
              {!item.is_latest && latestOf(item) ? (
                <button
                  type="button"
                  className="button button-secondary"
                  onClick={() => void compare(item, latestOf(item) as ProjectFile)}
                >
                  مقایسه نسخهٔ {item.version_number} با آخرین نسخهٔ {item.original_name}
                </button>
              ) : null}
              {comparison?.id === item.id ? (
                <span role="status" className="field-hint">
                  {comparison.text}
                </span>
              ) : null}
              {canSetBasis && item.downloadable ? (
                <button
                  type="button"
                  className="button button-secondary"
                  onClick={() => void toggleBasis(item)}
                >
                  {item.is_basis
                    ? `برداشتن مبنای متره از نسخهٔ ${item.version_number} ${item.original_name}`
                    : `ثبت نسخهٔ ${item.version_number} ${item.original_name} به‌عنوان مبنای متره`}
                </button>
              ) : null}
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
