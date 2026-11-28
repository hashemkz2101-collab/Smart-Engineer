"use client";

import { useState } from "react";

import { api, toApiError } from "../lib/api";
import {
  assumptionLabels,
  criteriaLabels,
  infeasibleLabels,
  layoutLimitationLabels,
  notEvaluatedLabels,
  strategyLabels,
  unplacedLabels,
  type Alternative,
  type LayoutData,
  type LayoutState,
} from "../lib/layouts";
import { requirementSections } from "../lib/requirements";
import { useResource } from "../lib/use-resource";

const kindLabels: Record<string, string> = Object.fromEntries(
  (requirementSections[0].lists?.[0]?.columns ?? [])
    .filter((column) => column.name === "kind")
    .flatMap((column) => column.choices ?? [])
    .map((choice) => [choice.value, choice.label]),
);

const fa = (value: number) => value.toLocaleString("fa-IR", { maximumFractionDigits: 2 });

function Drawing({ data, alternative, floor }: { data: LayoutData; alternative: Alternative; floor: number }) {
  const polygons = data.envelope_polygons ?? [];
  const points = polygons.flatMap((piece) => piece.exterior);
  if (points.length === 0) return null;
  const xs = points.map((p) => p[0]);
  const ys = points.map((p) => p[1]);
  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const minY = Math.min(...ys);
  const maxY = Math.max(...ys);
  const pad = Math.max(maxX - minX, maxY - minY) * 0.04;
  // Local plane: X right, Y up. SVG's Y points down, so every Y is mirrored explicitly.
  const sy = (y: number) => maxY - y;
  const placements = alternative.floors.find((item) => item.floor === floor)?.placements ?? [];
  return (
    <svg
      role="img"
      aria-label={`نمای بلوک‌های طبقهٔ ${floor} در گزینهٔ ${alternative.id}`}
      viewBox={`${minX - pad} ${-pad} ${maxX - minX + 2 * pad} ${maxY - minY + 2 * pad}`}
      className="layout-drawing"
      style={{ width: "100%", maxHeight: "28rem" }}
      direction="ltr"
    >
      {polygons.map((piece, index) => (
        <polygon
          key={index}
          points={piece.exterior.map(([x, y]) => `${x},${sy(y)}`).join(" ")}
          fill="none"
          stroke="currentColor"
          strokeDasharray="0.4 0.3"
          strokeWidth={Math.max(maxX - minX, maxY - minY) / 400}
        />
      ))}
      {placements.map((item) => (
        <g key={item.space_id}>
          <rect
            x={item.x}
            y={sy(item.y + item.height)}
            width={item.width}
            height={item.height}
            fill="currentColor"
            fillOpacity={0.12}
            stroke="currentColor"
            strokeWidth={Math.max(maxX - minX, maxY - minY) / 500}
          />
          <text
            x={item.x + item.width / 2}
            y={sy(item.y + item.height / 2)}
            textAnchor="middle"
            dominantBaseline="middle"
            fontSize={Math.max(0.5, Math.min(item.width, item.height) / 4)}
            fill="currentColor"
          >
            {item.space_id}
          </text>
        </g>
      ))}
    </svg>
  );
}

export function LayoutsPanel({
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
  const [picked, setPicked] = useState<string | null>(null);
  const [floor, setFloor] = useState(1);
  const resource = useResource<LayoutState>(`/projects/${projectId}/layouts`, version + reload);
  const state = resource.data;
  const data = state?.data ?? null;
  const alternative = data?.alternatives.find((item) => item.id === picked) ?? data?.alternatives[0];
  const activeFloor = alternative?.floors.some((item) => item.floor === floor) ? floor : 1;

  async function generate() {
    if (!state) return;
    setBusy(true);
    setMessage(null);
    try {
      await api.post(`/projects/${projectId}/layouts/generate`, { version: state.version });
      setMessage({ kind: "ok", text: "نتیجهٔ چیدمان از ورودی‌های فعلی ساخته و ذخیره شد." });
    } catch (error) {
      setMessage({ kind: "error", text: toApiError(error).userMessage });
    } finally {
      setBusy(false);
      setReload((current) => current + 1);
    }
  }

  return (
    <section className="detail-section" aria-labelledby="layouts-title">
      <h2 id="layouts-title">گزینه‌های چیدمان مفهومی</h2>
      <p className="field-hint">
        از محدودهٔ قابل ساخت و فهرست فضاها ساخته می‌شود. بلوک‌های مفهومی‌اند، نه پلان؛ معیارها و آنچه بررسی نشده با هر گزینه آمده است.
      </p>
      {resource.error ? (
        <p className="alert alert-error" role="alert">
          {resource.error.userMessage}
        </p>
      ) : null}
      {message ? (
        <div
          role={message.kind === "ok" ? "status" : "alert"}
          className={`alert alert-${message.kind === "ok" ? "success" : "error"}`}
        >
          {message.text}
        </div>
      ) : null}
      {state?.stale ? (
        <p className="alert alert-error" role="alert">
          زمین، ضوابط یا فهرست فضاها پس از ساخت این نتیجه تغییر کرده است؛ نتیجه قدیمی است و باید دوباره ساخته شود.
        </p>
      ) : null}
      {canEdit && state ? (
        <button className="button" type="button" disabled={busy} onClick={generate}>
          {busy ? "در حال ساخت…" : state.exists ? "ساخت دوبارهٔ گزینه‌ها" : "ساخت گزینه‌های چیدمان"}
        </button>
      ) : state ? (
        <p className="field-hint">فقط مالک و معمار پروژه می‌توانند گزینه‌ها را بسازند.</p>
      ) : resource.loading ? (
        <p className="status-text" role="status">
          در حال بارگذاری…
        </p>
      ) : null}

      {data && data.status === "infeasible" ? (
        <div className="alert alert-error" role="alert" data-testid="layout-infeasible">
          <p>گزینه‌ای ساخته نشد، به این دلایل:</p>
          <ul>
            {data.reasons.map((reason) => (
              <li key={reason}>{infeasibleLabels[reason] ?? reason}</li>
            ))}
          </ul>
        </div>
      ) : null}

      {data && alternative ? (
        <>
          <div className="tabs" role="group" aria-label="گزینه‌های چیدمان">
            {data.alternatives.map((item) => (
              <button
                key={item.id}
                type="button"
                className="tab"
                aria-pressed={item.id === alternative.id}
                onClick={() => {
                  setPicked(item.id);
                  setFloor(1);
                }}
              >
                {item.id}
              </button>
            ))}
          </div>
          <p data-testid="layout-strategy">{strategyLabels[alternative.strategy] ?? alternative.strategy}</p>
          <p>
            {fa(alternative.metrics.placed_spaces)} فضا جانمایی شد، {fa(alternative.metrics.unplaced_spaces)} فضا جانمایی نشد؛
            مجموع مساحت جانمایی‌شده {fa(alternative.metrics.placed_area_m2)} متر مربع در {fa(alternative.metrics.floors_used)} طبقه.
          </p>
          {alternative.floors.length > 1 ? (
            <div className="tabs" role="group" aria-label="طبقه‌ها">
              {alternative.floors.map((item) => (
                <button
                  key={item.floor}
                  type="button"
                  className="tab"
                  aria-pressed={item.floor === activeFloor}
                  onClick={() => setFloor(item.floor)}
                >
                  طبقهٔ {fa(item.floor)}
                </button>
              ))}
            </div>
          ) : null}
          <Drawing data={data} alternative={alternative} floor={activeFloor} />
          <div className="table-wrap">
            <table>
              <caption className="visually-hidden">بلوک‌های طبقهٔ {activeFloor}</caption>
              <thead>
                <tr>
                  <th scope="col">کد</th>
                  <th scope="col">نوع</th>
                  <th scope="col">ابعاد (متر)</th>
                  <th scope="col">مساحت (متر مربع)</th>
                </tr>
              </thead>
              <tbody>
                {(alternative.floors.find((item) => item.floor === activeFloor)?.placements ?? []).map((item) => (
                  <tr key={item.space_id}>
                    <td>{item.space_id}</td>
                    <td>{kindLabels[item.kind] ?? item.kind}</td>
                    <td>
                      {fa(item.width)} × {fa(item.height)}
                    </td>
                    <td>
                      {fa(item.area_m2)}
                      {item.area_basis === "range_midpoint" ? " (میانهٔ بازه)" : ""}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {alternative.unplaced.length ? (
            <>
              <h3>فضاهای جانمایی‌نشده</h3>
              <ul aria-label="فضاهای جانمایی‌نشده">
                {alternative.unplaced.map((item) => (
                  <li key={item.space_id}>
                    {item.space_id} ({kindLabels[item.kind] ?? item.kind}): {unplacedLabels[item.reason] ?? item.reason}
                  </li>
                ))}
              </ul>
            </>
          ) : null}
          <h3>معیارها</h3>
          <ul aria-label="معیارها">
            {alternative.criteria.map((code) => (
              <li key={code}>{criteriaLabels[code] ?? code}</li>
            ))}
            {alternative.assumptions.map((code) => (
              <li key={code}>{assumptionLabels[code] ?? code}</li>
            ))}
          </ul>
          <h3>بررسی‌نشده</h3>
          <ul className="field-hint" aria-label="بررسی‌نشده">
            {alternative.not_evaluated.map((code) => (
              <li key={code}>{notEvaluatedLabels[code] ?? code}</li>
            ))}
          </ul>
          <ul className="field-hint" aria-label="محدودیت‌ها">
            {alternative.limitations.map((code) => (
              <li key={code}>{layoutLimitationLabels[code] ?? code}</li>
            ))}
          </ul>
        </>
      ) : null}
    </section>
  );
}
