"use client";

import { useState, type FormEvent } from "react";

import { api, ApiError, toApiError } from "../lib/api";
import { fieldReasonMessages } from "../lib/messages";
import {
  fieldLabel,
  siteSections,
  type SiteField,
  type SiteList,
  type SiteSectionDef,
} from "../lib/site";
import { useResource } from "../lib/use-resource";
import { FormField } from "./form-field";

type Row = Record<string, string | boolean>;
type Derived = {
  status: "match" | "discrepancy" | "no_declared_area" | "not_computable";
  computed_area_m2: number | null;
  declared_area_m2: number | null;
  difference_m2: number | null;
  difference_percent: number | null;
  tolerance_percent: number;
  computed_side_lengths_m: number[];
};
type SectionState = {
  section: string;
  data: Record<string, unknown>;
  complete: boolean;
  missing: string[];
  not_provided: string[];
  version: number;
  derived?: Derived;
};

function reasonText(reason: string): string {
  return fieldReasonMessages[reason] ?? "مقدار درست نیست.";
}

// Errors come as {field: path, reason}; a path may be "vertices[2].x".
function errorsFrom(error: ApiError): { scalar: Record<string, string>; list: Record<string, string[]> } {
  const scalar: Record<string, string> = {};
  const list: Record<string, string[]> = {};
  for (const detail of error.details) {
    const item = detail as { field?: unknown; reason?: unknown };
    if (typeof item.field !== "string" || typeof item.reason !== "string") continue;
    const match = /^(\w+)\[(\d+)\](?:\.(\w+))?$/.exec(item.field);
    if (match) {
      const column = match[3] ? ` (${match[3]})` : "";
      (list[match[1]] ??= []).push(`ردیف ${Number(match[2]) + 1}${column}: ${reasonText(item.reason)}`);
    } else if (/^\w+$/.test(item.field)) {
      scalar[item.field] = reasonText(item.reason);
    }
  }
  return { scalar, list };
}

function toRows(list: SiteList, raw: unknown): Row[] {
  if (!Array.isArray(raw)) return [];
  return raw.map((entry) => {
    const row: Row = {};
    for (const column of list.columns) {
      const value = (entry as Record<string, unknown>)[column.name];
      row[column.name] = column.kind === "boolean" ? value === true : value === undefined ? "" : String(value);
    }
    return row;
  });
}

function rowIsEmpty(row: Row): boolean {
  return Object.values(row).every((value) => value === "" || value === false);
}

function payloadRows(rows: Row[]): Row[] {
  return rows.filter((row) => !rowIsEmpty(row)).map((row) => {
    const out: Row = {};
    for (const [key, value] of Object.entries(row)) {
      if (value !== "") out[key] = value;
    }
    return out;
  });
}

function ScalarInput({
  def,
  value,
  error,
  disabled,
  onChange,
}: {
  def: SiteField;
  value: string;
  error?: string;
  disabled: boolean;
  onChange: (value: string) => void;
}) {
  const id = `site-${def.name}`;
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

function ListEditor({
  list,
  rows,
  errors,
  disabled,
  onChange,
}: {
  list: SiteList;
  rows: Row[];
  errors: string[];
  disabled: boolean;
  onChange: (rows: Row[]) => void;
}) {
  const blank: Row = Object.fromEntries(
    list.columns.map((column) => [column.name, column.kind === "boolean" ? false : ""]),
  );
  const update = (index: number, name: string, value: string | boolean) =>
    onChange(rows.map((row, at) => (at === index ? { ...row, [name]: value } : row)));
  return (
    <fieldset className="plain-fieldset site-list" disabled={disabled}>
      <legend>{list.label}</legend>
      {list.hint ? <p className="field-hint">{list.hint}</p> : null}
      {rows.length === 0 ? <p className="field-hint">موردی ثبت نشده است.</p> : null}
      {rows.map((row, index) => (
        <div className="site-row" role="group" aria-label={`${list.label}، ردیف ${index + 1}`} key={index}>
          {list.columns.map((column) => {
            const id = `site-${list.name}-${index}-${column.name}`;
            const label = column.required ? `${column.label} (ضروری)` : column.label;
            const accessible = `${list.label} ${index + 1}: ${label}`;
            if (column.kind === "boolean") {
              return (
                <label className="site-check" key={column.name} htmlFor={id}>
                  <input
                    id={id}
                    type="checkbox"
                    checked={row[column.name] === true}
                    onChange={(event) => update(index, column.name, event.target.checked)}
                  />{" "}
                  {column.label}
                </label>
              );
            }
            return (
              <div className="form-field" key={column.name}>
                <label htmlFor={id}>{accessible}</label>
                {column.kind === "choice" ? (
                  <select
                    id={id}
                    value={String(row[column.name])}
                    onChange={(event) => update(index, column.name, event.target.value)}
                  >
                    <option value="">انتخاب نشده</option>
                    {column.choices?.map((choice) => (
                      <option key={choice.value} value={choice.value}>
                        {choice.label}
                      </option>
                    ))}
                  </select>
                ) : (
                  <input
                    id={id}
                    type="text"
                    dir={column.ltr ? "ltr" : undefined}
                    inputMode={column.kind === "number" ? "decimal" : undefined}
                    value={String(row[column.name])}
                    onChange={(event) => update(index, column.name, event.target.value)}
                  />
                )}
              </div>
            );
          })}
          <button
            type="button"
            className="button button-secondary"
            onClick={() => onChange(rows.filter((_, at) => at !== index))}
          >
            حذف ردیف {index + 1} از {list.label}
          </button>
        </div>
      ))}
      <button
        type="button"
        className="button button-secondary"
        onClick={() => onChange([...rows, { ...blank }])}
      >
        افزودن ردیف به {list.label}
      </button>
      {errors.length > 0 ? (
        <ul className="field-error" aria-label={`خطاهای ${list.label}`}>
          {errors.map((message) => (
            <li key={message}>{message}</li>
          ))}
        </ul>
      ) : null}
    </fieldset>
  );
}

function AreaReport({ derived }: { derived: Derived }) {
  const number = (value: number | null) => (value === null ? "" : String(value));
  let text: string;
  switch (derived.status) {
    case "match":
      text = `مساحت محاسبه‌شده (${number(derived.computed_area_m2)} متر مربع) با مساحت اظهارشده هم‌خوان است؛ اختلاف ${number(derived.difference_percent)}٪ و در حد مجاز ${derived.tolerance_percent}٪ است.`;
      break;
    case "discrepancy":
      text = `اختلاف مساحت: محاسبه‌شده ${number(derived.computed_area_m2)} و اظهارشده ${number(derived.declared_area_m2)} متر مربع؛ اختلاف ${number(derived.difference_m2)} متر مربع (${number(derived.difference_percent)}٪). این اختلاف باید بررسی شود.`;
      break;
    case "no_declared_area":
      text = `مساحت اظهارشده وارد نشده است؛ مساحت محاسبه‌شده ${number(derived.computed_area_m2)} متر مربع است.`;
      break;
    default:
      text = "مساحت هنوز قابل محاسبه نیست؛ ابعاد مستطیل یا دست‌کم سه رأس مرز را وارد کنید.";
  }
  return (
    <div className="area-report" data-testid="area-report" data-status={derived.status}>
      <p>{text}</p>
      {derived.computed_side_lengths_m.length > 0 ? (
        <p className="field-hint" dir="ltr">
          {derived.computed_side_lengths_m.join(" · ")}
        </p>
      ) : null}
    </div>
  );
}

function SectionForm({
  projectId,
  def,
  state,
  canEdit,
  onSaved,
  onConflict,
}: {
  projectId: string;
  def: SiteSectionDef;
  state: SectionState;
  canEdit: boolean;
  onSaved: (message: string) => void;
  onConflict: () => void;
}) {
  const [values, setValues] = useState<Record<string, string>>(() =>
    Object.fromEntries(def.fields.map((field) => [field.name, String(state.data[field.name] ?? "")])),
  );
  const [lists, setLists] = useState<Record<string, Row[]>>(() =>
    Object.fromEntries(def.lists.map((list) => [list.name, toRows(list, state.data[list.name])])),
  );
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [listErrors, setListErrors] = useState<Record<string, string[]>>({});
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function save(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setFieldErrors({});
    setListErrors({});
    const data: Record<string, unknown> = { ...values };
    for (const list of def.lists) {
      const rows = payloadRows(lists[list.name]);
      if (rows.length > 0 || list.always) data[list.name] = rows;
    }
    try {
      const saved = await api.put<SectionState>(`/projects/${projectId}/site/${def.key}`, {
        data,
        version: state.version,
      });
      const labels = saved.missing.map((name) => fieldLabel(def, name));
      onSaved(
        saved.complete
          ? "ذخیره شد؛ این بخش کامل است."
          : `ذخیره شد. برای تکمیل این بخش لازم است: ${labels.join("، ")}.`,
      );
    } catch (failure) {
      const apiError = toApiError(failure);
      const parsed = errorsFrom(apiError);
      setFieldErrors(parsed.scalar);
      setListErrors(parsed.list);
      setError(apiError.userMessage);
      if (apiError.code === "version_conflict") onConflict();
    }
    setBusy(false);
  }

  const titleId = "site-section-title";
  return (
    <form className="form-panel" onSubmit={save} noValidate aria-labelledby={titleId}>
      <h3 id={titleId}>{def.title}</h3>
      {def.intro ? <p className="field-hint">{def.intro}</p> : null}
      {def.key === "parcel" && state.derived ? <AreaReport derived={state.derived} /> : null}
      {def.key === "soil" ? (
        <p className="field-hint" data-testid="soil-not-provided">
          {state.not_provided.length === 0
            ? "همهٔ مقادیر خاک ثبت شده‌اند."
            : `ثبت‌نشده: ${state.not_provided.map((name) => fieldLabel(def, name)).join("، ")}.`}
        </p>
      ) : null}
      <fieldset className="plain-fieldset" disabled={!canEdit || busy}>
        <legend className="visually-hidden">{def.title}</legend>
        {def.fields.map((field) => (
          <ScalarInput
            key={field.name}
            def={field}
            value={values[field.name]}
            error={fieldErrors[field.name]}
            disabled={!canEdit}
            onChange={(next) => setValues((current) => ({ ...current, [field.name]: next }))}
          />
        ))}
        {def.lists.map((list) => (
          <ListEditor
            key={list.name}
            list={list}
            rows={lists[list.name]}
            errors={[...(listErrors[list.name] ?? []), ...(fieldErrors[list.name] ? [fieldErrors[list.name]] : [])]}
            disabled={!canEdit}
            onChange={(rows) => setLists((current) => ({ ...current, [list.name]: rows }))}
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
          {busy ? "در حال ذخیره…" : "ذخیرهٔ این بخش"}
        </button>
      ) : (
        <p className="field-hint">فقط مالک و معمار پروژه می‌توانند این اطلاعات را ویرایش کنند.</p>
      )}
    </form>
  );
}

export function SitePanel({
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
  const [selected, setSelected] = useState(siteSections[0].key);
  const site = useResource<{ sections: SectionState[] }>(
    `/projects/${projectId}/site`,
    version + reload,
  );
  const bump = () => setReload((current) => current + 1);

  const def = siteSections.find((section) => section.key === selected) ?? siteSections[0];
  const state = site.data?.sections.find((section) => section.section === def.key);

  return (
    <section className="detail-section" aria-labelledby="site-title">
      <h2 id="site-title">داده‌های زمین</h2>
      <p className="field-hint">
        هر بخش را می‌توانید ناقص ذخیره کنید. مقدارهای وارد‌نشده هرگز با مقدار پیش‌فرض پر نمی‌شوند.
      </p>
      {site.error ? (
        <p className="alert alert-error" role="alert">
          {site.error.userMessage}
        </p>
      ) : null}
      <div className="tabs" role="group" aria-label="بخش‌های داده‌های زمین">
        {siteSections.map((section) => {
          const info = site.data?.sections.find((item) => item.section === section.key);
          const status = !info || info.version === 0 ? "شروع نشده" : info.complete ? "کامل" : "پیش‌نویس";
          return (
            <button
              key={section.key}
              type="button"
              className="tab"
              aria-pressed={selected === section.key}
              onClick={() => {
                setSelected(section.key);
                setNotice(null);
              }}
            >
              {section.title} <span className="badge">{status}</span>
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
        <SectionForm
          key={`${def.key}-${state.version}`}
          projectId={projectId}
          def={def}
          state={state}
          canEdit={canEdit}
          onSaved={(message) => {
            setNotice(message);
            bump();
          }}
          onConflict={bump}
        />
      ) : site.loading ? (
        <p className="status-text" role="status">
          در حال بارگذاری…
        </p>
      ) : null}
    </section>
  );
}
