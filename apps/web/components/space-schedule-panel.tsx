"use client";

import { useState } from "react";

import { api, toApiError } from "../lib/api";
import { requirementSections } from "../lib/requirements";
import { flagLabels, limitationLabels, type ScheduleState } from "../lib/space-schedule";
import { useResource } from "../lib/use-resource";

const kindLabels: Record<string, string> = Object.fromEntries(
  (requirementSections[0].lists?.[0]?.columns ?? [])
    .filter((column) => column.name === "kind")
    .flatMap((column) => column.choices ?? [])
    .map((choice) => [choice.value, choice.label]),
);

function area(space: { target_area_m2?: number; area_min_m2?: number; area_max_m2?: number }): string {
  const parts: string[] = [];
  if (space.target_area_m2 !== undefined) parts.push(`هدف ${space.target_area_m2.toLocaleString("fa-IR")}`);
  if (space.area_min_m2 !== undefined || space.area_max_m2 !== undefined) {
    const low = space.area_min_m2 === undefined ? "—" : space.area_min_m2.toLocaleString("fa-IR");
    const high = space.area_max_m2 === undefined ? "—" : space.area_max_m2.toLocaleString("fa-IR");
    parts.push(`بازه ${low} تا ${high}`);
  }
  return parts.length ? parts.join("، ") : "ثبت نشده";
}

export function SpaceSchedulePanel({
  projectId,
  canEdit,
  version,
}: {
  projectId: string;
  canEdit: boolean;
  version: number;
}) {
  const [reload, setReload] = useState(0);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<{ kind: "ok" | "error"; text: string } | null>(null);
  const resource = useResource<ScheduleState>(
    `/projects/${projectId}/space-schedule`,
    version + reload,
  );
  const state = resource.data;
  const data = state?.data ?? null;

  async function generate() {
    if (!state) return;
    setBusy(true);
    setMessage(null);
    try {
      await api.post(`/projects/${projectId}/space-schedule/generate`, { version: state.version });
      setMessage({ kind: "ok", text: "فهرست فضاها از برنامهٔ فعلی ساخته و ذخیره شد." });
    } catch (error) {
      setMessage({ kind: "error", text: toApiError(error).userMessage });
    } finally {
      setBusy(false);
      setReload((current) => current + 1);
    }
  }

  return (
    <section className="detail-section" aria-labelledby="schedule-title">
      <h2 id="schedule-title">فهرست فضاها</h2>
      <p className="field-hint">
        فهرست از «برنامهٔ فیزیکی» نیازمندی‌ها ساخته می‌شود. چیزی حدس زده نمی‌شود؛ مقدارهای وارد‌نشده با پرچم نشان داده می‌شوند.
      </p>
      {resource.error ? (
        <p className="alert alert-error" role="alert">
          {resource.error.userMessage}
        </p>
      ) : null}
      {message ? (
        <div role={message.kind === "ok" ? "status" : "alert"} className={`alert alert-${message.kind === "ok" ? "success" : "error"}`}>
          {message.text}
        </div>
      ) : null}
      {state && !state.program_ready ? (
        <p className="field-hint">
          ابتدا بخش «برنامه» را در نیازمندی‌ها کامل ذخیره کنید (تعداد واحد، تعداد طبقه و فهرست اتاق‌ها).
        </p>
      ) : null}
      {state?.stale ? (
        <p className="alert alert-error" role="alert">
          برنامه پس از ساخت این فهرست تغییر کرده است؛ فهرست قدیمی است و باید دوباره ساخته شود.
        </p>
      ) : null}
      {canEdit && state ? (
        <button className="button" type="button" disabled={busy || !state.program_ready} onClick={generate}>
          {busy ? "در حال ساخت…" : state.exists ? "ساخت دوبارهٔ فهرست" : "ساخت فهرست فضاها"}
        </button>
      ) : state ? (
        <p className="field-hint">فقط مالک و معمار پروژه می‌توانند فهرست را بسازند.</p>
      ) : resource.loading ? (
        <p className="status-text" role="status">
          در حال بارگذاری…
        </p>
      ) : null}

      {data ? (
        <>
          <p data-testid="schedule-totals">
            {data.totals.spaces.toLocaleString("fa-IR")} فضا در {data.totals.rooms.toLocaleString("fa-IR")} ردیف؛ مجموع خالص:{" "}
            {data.totals.area_lower_m2.toLocaleString("fa-IR")} تا {data.totals.area_upper_m2.toLocaleString("fa-IR")} متر مربع
            {data.totals.bounds_complete ? "" : " (ناقص: بعضی فضاها مساحت ندارند)"}
          </p>
          {data.flags.length ? (
            <ul className="flag-list" aria-label="پرچم‌ها و موارد ناتمام">
              {data.flags.map((flag, index) => (
                <li key={`${flag.code}-${flag.room_index ?? "all"}-${index}`}>
                  {flag.room_index === undefined ? "" : `ردیف ${(flag.room_index + 1).toLocaleString("fa-IR")}: `}
                  {flagLabels[flag.code] ?? flag.code}
                </li>
              ))}
            </ul>
          ) : (
            <p className="field-hint">هیچ پرچمی ثبت نشد.</p>
          )}
          <div className="table-wrap">
            <table>
              <caption className="visually-hidden">فهرست فضاها</caption>
              <thead>
                <tr>
                  <th scope="col">کد</th>
                  <th scope="col">نوع</th>
                  <th scope="col">نام</th>
                  <th scope="col">مساحت (متر مربع)</th>
                </tr>
              </thead>
              <tbody>
                {data.spaces.map((space) => (
                  <tr key={space.id}>
                    <td>{space.id}</td>
                    <td>{kindLabels[space.kind] ?? space.kind}</td>
                    <td>
                      {space.name ?? "—"}
                      {space.of > 1 ? ` (${space.ordinal.toLocaleString("fa-IR")} از ${space.of.toLocaleString("fa-IR")})` : ""}
                    </td>
                    <td>{area(space)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <ul className="field-hint" aria-label="محدودیت‌ها">
            {data.limitations.map((code) => (
              <li key={code}>{limitationLabels[code] ?? code}</li>
            ))}
          </ul>
        </>
      ) : null}
    </section>
  );
}
