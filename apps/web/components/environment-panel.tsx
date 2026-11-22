"use client";

import { useState, type FormEvent } from "react";

import { api, ApiError, toApiError } from "../lib/api";
import { fieldReasonMessages } from "../lib/messages";
import type { SiteField } from "../lib/site";
import {
  environmentFields,
  environmentMissingLabels,
  environmentSourceFields,
} from "../lib/environment";
import { statusLabels, type ZoningDef } from "../lib/zoning";
import { useResource } from "../lib/use-resource";
import { FormField } from "./form-field";

type RecordState = {
  field: string;
  data: Record<string, unknown>;
  status: "unknown" | "needs_inquiry" | "verified";
  source_missing: string[];
  version: number;
};

function errorsFrom(error: ApiError): Record<string, string> {
  const result: Record<string, string> = {};
  for (const detail of error.details) {
    const item = detail as { field?: unknown; reason?: unknown };
    if (typeof item.field === "string" && typeof item.reason === "string") {
      result[item.field] = fieldReasonMessages[item.reason] ?? "مقدار درست نیست.";
    }
  }
  return result;
}

function Input({
  def,
  value,
  error,
  disabled,
  onChange,
}: {
  def: SiteField;
  value: string | boolean;
  error?: string;
  disabled: boolean;
  onChange: (value: string | boolean) => void;
}) {
  const id = `env-${def.name}`;
  if (def.kind === "boolean") {
    return (
      <div className="form-field">
        <label className="site-check" htmlFor={id}>
          <input
            id={id}
            type="checkbox"
            disabled={disabled}
            checked={value === true}
            onChange={(event) => onChange(event.target.checked)}
          />{" "}
          {def.label}
        </label>
      </div>
    );
  }
  const describedBy = [error ? `${id}-error` : null, def.hint ? `${id}-hint` : null]
    .filter(Boolean)
    .join(" ");
  const common = {
    id,
    disabled,
    "aria-invalid": error ? true : undefined,
    "aria-describedby": describedBy || undefined,
    dir: def.ltr ? ("ltr" as const) : undefined,
    value: String(value),
  };
  return (
    <FormField id={id} label={def.label} hint={def.hint}>
      {def.kind === "choice" ? (
        <select {...common} onChange={(event) => onChange(event.target.value)}>
          <option value="">انتخاب نشده</option>
          {def.choices?.map((choice) => (
            <option key={choice.value} value={choice.value}>
              {choice.label}
            </option>
          ))}
        </select>
      ) : def.kind === "textarea" ? (
        <textarea {...common} rows={3} onChange={(event) => onChange(event.target.value)} />
      ) : (
        <input
          {...common}
          type="text"
          inputMode={def.kind === "number" ? "decimal" : undefined}
          onChange={(event) => onChange(event.target.value)}
        />
      )}
      {error ? (
        <p className="field-error" id={`${id}-error`}>
          {error}
        </p>
      ) : null}
    </FormField>
  );
}

function StatusLine({ state }: { state: RecordState }) {
  const missing = state.source_missing.map((name) => environmentMissingLabels[name] ?? name);
  return (
    <p className="area-report" data-testid="env-status" data-status={state.status}>
      وضعیت: <strong>{statusLabels[state.status]}</strong>
      {state.status === "unknown" ? " — هنوز مقداری ثبت نشده است." : null}
      {state.status === "needs_inquiry"
        ? ` — مقدار بدون منبع کامل و تأییدشده است و باید استعلام شود.${
            missing.length > 0 ? ` کمبود منبع: ${missing.join("، ")}.` : ""
          }`
        : null}
    </p>
  );
}

function RecordForm({
  projectId,
  def,
  state,
  canEdit,
  onSaved,
  onConflict,
}: {
  projectId: string;
  def: ZoningDef;
  state: RecordState;
  canEdit: boolean;
  onSaved: (message: string, saved: RecordState) => void;
  onConflict: () => void;
}) {
  const all = [...def.fields, ...environmentSourceFields];
  const [values, setValues] = useState<Record<string, string | boolean>>(() =>
    Object.fromEntries(
      all.map((field) => {
        const stored = state.data[field.name];
        return [field.name, field.kind === "boolean" ? stored === true : String(stored ?? "")];
      }),
    ),
  );
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function save(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setFieldErrors({});
    const data: Record<string, string | boolean> = {};
    for (const [key, value] of Object.entries(values)) {
      if (value !== "" && value !== false) data[key] = value;
    }
    try {
      const saved = await api.put<RecordState>(`/projects/${projectId}/environment/${def.key}`, {
        data,
        version: state.version,
      });
      onSaved(`ذخیره شد؛ وضعیت: ${statusLabels[saved.status]}.`, saved);
    } catch (failure) {
      const apiError = toApiError(failure);
      setFieldErrors(errorsFrom(apiError));
      setError(apiError.userMessage);
      if (apiError.code === "version_conflict") onConflict();
    }
    setBusy(false);
  }

  const titleId = "env-record-title";
  return (
    <form className="form-panel" onSubmit={save} noValidate aria-labelledby={titleId}>
      <h3 id={titleId}>{def.title}</h3>
      <StatusLine state={state} />
      <fieldset className="plain-fieldset" disabled={!canEdit || busy}>
        <legend>مقدار ثبت‌شده</legend>
        {def.fields.map((field) => (
          <Input
            key={field.name}
            def={field}
            value={values[field.name]}
            error={fieldErrors[field.name]}
            disabled={!canEdit}
            onChange={(next) => setValues((current) => ({ ...current, [field.name]: next }))}
          />
        ))}
      </fieldset>
      <fieldset className="plain-fieldset" disabled={!canEdit || busy}>
        <legend>منبع و سند</legend>
        {environmentSourceFields.map((field) => (
          <Input
            key={field.name}
            def={field}
            value={values[field.name]}
            error={fieldErrors[field.name]}
            disabled={!canEdit}
            onChange={(next) => setValues((current) => ({ ...current, [field.name]: next }))}
          />
        ))}
      </fieldset>
      {error ? (
        <div role="alert" className="alert alert-error">
          {error}
        </div>
      ) : null}
      {canEdit ? (
        <button className="button" type="submit" disabled={busy}>
          {busy ? "در حال ذخیره…" : "ذخیرهٔ این مورد"}
        </button>
      ) : (
        <p className="field-hint">فقط مالک، معمار و مهندسان پروژه می‌توانند این اطلاعات را ویرایش کنند.</p>
      )}
    </form>
  );
}

export function EnvironmentPanel({
  projectId,
  canEdit,
  version,
}: {
  projectId: string;
  canEdit: boolean;
  version: number;
}) {
  const [reload, setReload] = useState(0);
  const [notice, setNotice] = useState<string | null>(null);
  const [selected, setSelected] = useState(environmentFields[0].key);
  const env = useResource<{ records: RecordState[] }>(
    `/projects/${projectId}/environment`,
    version + reload,
  );
  const bump = () => setReload((current) => current + 1);
  // The saved response replaces the form at once, so edits made while the list reloads
  // are never thrown away by a late refetch.
  const [saved, setSaved] = useState<Record<string, RecordState>>({});
  const latest = (key: string) => {
    const fetched = env.data?.records.find((item) => item.field === key);
    const local = saved[key];
    return local && (!fetched || local.version >= fetched.version) ? local : fetched;
  };

  const def = environmentFields.find((item) => item.key === selected) ?? environmentFields[0];
  const state = latest(def.key);

  return (
    <section className="detail-section" aria-labelledby="env-title">
      <h2 id="env-title">شرایط محیطی و فنی</h2>
      <p className="field-hint">
        این بخش فقط مقدارهایی را ثبت می‌کند که شما از منبع معتبر وارد می‌کنید. منبع، محل و تاریخ داده باید
        کامل و تأییدشده باشد؛ وگرنه مقدار «نیازمند استعلام» می‌ماند و مقداری که وارد نشود «نامشخص» است.
      </p>
      {env.error ? (
        <p className="alert alert-error" role="alert">
          {env.error.userMessage}
        </p>
      ) : null}
      <div className="tabs" role="group" aria-label="دسته‌های شرایط محیطی">
        {environmentFields.map((item) => {
          const info = latest(item.key);
          return (
            <button
              key={item.key}
              type="button"
              className="tab"
              aria-pressed={selected === item.key}
              onClick={() => {
                setSelected(item.key);
                setNotice(null);
              }}
            >
              {item.title} <span className="badge">{statusLabels[info?.status ?? "unknown"]}</span>
            </button>
          );
        })}
      </div>
      {notice ? (
        <div role="status" className="alert alert-success">
          {notice}
        </div>
      ) : null}
      {state ? (
        <RecordForm
          key={`${def.key}-${state.version}`}
          projectId={projectId}
          def={def}
          state={state}
          canEdit={canEdit}
          onSaved={(message, payload) => {
            setSaved((current) => ({ ...current, [def.key]: payload }));
            setNotice(message);
            bump();
          }}
          onConflict={bump}
        />
      ) : env.loading ? (
        <p className="status-text" role="status">
          در حال بارگذاری…
        </p>
      ) : null}
    </section>
  );
}
