"use client";

import { useState, type FormEvent } from "react";

import { api, ApiError, toApiError } from "../lib/api";
import { intakeSteps, type FieldDef, type StepDef } from "../lib/intake";
import { fieldReasonMessages } from "../lib/messages";
import { useResource } from "../lib/use-resource";
import { FormError, FormField, FormNotice } from "./form-field";

type StepState = {
  step: string;
  data: Record<string, string | number>;
  complete: boolean;
  missing: string[];
  version: number;
};

function fieldErrorsFrom(error: ApiError): Record<string, string> {
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
  def: FieldDef;
  value: string;
  error?: string;
  disabled: boolean;
  onChange: (value: string) => void;
}) {
  const id = `intake-${def.name}`;
  const describedBy = [error ? `${id}-error` : null, def.hint ? `${id}-hint` : null]
    .filter(Boolean)
    .join(" ");
  const common = {
    id,
    disabled,
    "aria-invalid": error ? true : undefined,
    "aria-describedby": describedBy || undefined,
    dir: def.ltr ? ("ltr" as const) : undefined,
  };
  return (
    <FormField id={id} label={def.required ? `${def.label} (ضروری)` : def.label} hint={def.hint}>
      {def.kind === "choice" ? (
        <select {...common} value={value} onChange={(event) => onChange(event.target.value)}>
          <option value="">انتخاب نشده</option>
          {def.choices?.map((choice) => (
            <option key={choice.value} value={choice.value}>
              {choice.label}
            </option>
          ))}
        </select>
      ) : def.kind === "textarea" ? (
        <textarea {...common} rows={3} value={value} onChange={(event) => onChange(event.target.value)} />
      ) : (
        <input
          {...common}
          type="text"
          inputMode={def.kind === "number" ? "decimal" : undefined}
          value={value}
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

function StepForm({
  projectId,
  def,
  state,
  canEdit,
  onSaved,
  onConflict,
}: {
  projectId: string;
  def: StepDef;
  state: StepState;
  canEdit: boolean;
  onSaved: (message: string, saved: StepState) => void;
  onConflict: () => void;
}) {
  const [values, setValues] = useState<Record<string, string>>(() =>
    Object.fromEntries(def.fields.map((field) => [field.name, String(state.data[field.name] ?? "")])),
  );
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function save(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setFieldErrors({});
    try {
      const saved = await api.put<StepState>(`/projects/${projectId}/intake/${def.key}`, {
        data: values,
        version: state.version,
      });
      const labels = def.fields
        .filter((field) => saved.missing.includes(field.name))
        .map((field) => field.label);
      onSaved(
        saved.complete
          ? "ذخیره شد؛ این مرحله کامل است."
          : `ذخیره شد. برای تکمیل این مرحله لازم است: ${labels.join("، ")}.`,
        saved,
      );
    } catch (failure) {
      const apiError = toApiError(failure);
      setFieldErrors(fieldErrorsFrom(apiError));
      setError(apiError.userMessage);
      if (apiError.code === "version_conflict") onConflict();
    }
    setBusy(false);
  }

  return (
    <form className="form-panel" onSubmit={save} noValidate aria-labelledby="intake-step-title">
      <h3 id="intake-step-title">{def.title}</h3>
      {def.key === "legal" ? (
        <p className="field-hint">
          این بخش فقط اظهارات شما را ثبت می‌کند؛ اعتبار حقوقی سند یا مالکیت بررسی نمی‌شود.
        </p>
      ) : null}
      <fieldset className="plain-fieldset" disabled={!canEdit || busy}>
        <legend className="visually-hidden">{def.title}</legend>
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
      <FormError message={error} />
      {canEdit ? (
        <button className="button" type="submit" disabled={busy}>
          {busy ? "در حال ذخیره…" : "ذخیرهٔ این مرحله"}
        </button>
      ) : (
        <p className="field-hint">فقط مالک پروژه می‌تواند این اطلاعات را ویرایش کند.</p>
      )}
    </form>
  );
}

export function IntakePanel({
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
  const [selected, setSelected] = useState(intakeSteps[0].key);
  const intake = useResource<{ steps: StepState[] }>(
    `/projects/${projectId}/intake`,
    version + reload,
  );
  const bump = () => setReload((current) => current + 1);
  // The saved response replaces the form at once, so edits made while the list reloads
  // are never thrown away by a late refetch (the form is keyed by version).
  const [saved, setSaved] = useState<Record<string, StepState>>({});
  const latest = (key: string) => {
    const fetched = intake.data?.steps.find((item) => item.step === key);
    const local = saved[key];
    return local && (!fetched || local.version >= fetched.version) ? local : fetched;
  };

  const def = intakeSteps.find((step) => step.key === selected) ?? intakeSteps[0];
  const state = latest(def.key);

  return (
    <section className="detail-section" aria-labelledby="intake-title">
      <h2 id="intake-title">اطلاعات ورودی پروژه</h2>
      <p className="field-hint">
        هر مرحله را می‌توانید ناقص ذخیره کنید و بعداً ادامه دهید.
      </p>
      {intake.error ? (
        <p className="alert alert-error" role="alert">
          {intake.error.userMessage}
        </p>
      ) : null}
      <div className="tabs" role="group" aria-label="مراحل اطلاعات ورودی">
        {intakeSteps.map((step) => {
          const info = latest(step.key);
          const status = !info || info.version === 0 ? "شروع نشده" : info.complete ? "کامل" : "پیش‌نویس";
          return (
            <button
              key={step.key}
              type="button"
              className="tab"
              aria-pressed={selected === step.key}
              onClick={() => {
                setSelected(step.key);
                setNotice(null);
              }}
            >
              {step.title} <span className="badge">{status}</span>
            </button>
          );
        })}
      </div>
      <FormNotice message={notice} />
      {state ? (
        <StepForm
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
      ) : intake.loading ? (
        <p className="status-text" role="status">
          در حال بارگذاری…
        </p>
      ) : null}
    </section>
  );
}
