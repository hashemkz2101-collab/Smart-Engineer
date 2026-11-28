"use client";

import { useState, type FormEvent } from "react";

import { api, toApiError } from "../lib/api";
import {
  operationLabels,
  type AiProposal,
  type AiStatus,
  snapChoices,
  typeLabels,
  unitFactors,
  unitNames,
  verticalKinds,
  wallLength,
  type DesignElement,
  type DesignHistory,
  type DesignOperation,
  type DesignState,
  type LengthUnit,
} from "../lib/design";
import type { LayoutState } from "../lib/layouts";
import { requirementSections } from "../lib/requirements";
import { messageForCode } from "../lib/messages";
import { useResource } from "../lib/use-resource";

const kindChoices = (requirementSections[0].lists?.[0]?.columns ?? [])
  .filter((column) => column.name === "kind")
  .flatMap((column) => column.choices ?? []);
const kindLabels: Record<string, string> = Object.fromEntries(kindChoices.map((c) => [c.value, c.label]));

const fa = (value: number) => value.toLocaleString("fa-IR", { maximumFractionDigits: 3 });
const num = (form: FormData, name: string) => Number(form.get(name));

function describe(element: DesignElement): string {
  const base = `${element.id} — ${typeLabels[element.type]}`;
  if (element.type === "vertical") return `${base} ${verticalKinds[element.kind ?? ""] ?? element.kind ?? ""}`;
  if (element.type === "space") return `${base} ${element.name ?? kindLabels[element.kind ?? ""] ?? element.kind ?? ""}`;
  return element.label ? `${base} ${element.label}` : base;
}

function Drawing({ elements, selected, onPick }: { elements: DesignElement[]; selected: string | null; onPick: (id: string) => void }) {
  const walls = new Map(elements.filter((e) => e.type === "wall").map((w) => [w.id, w]));
  const xs: number[] = [];
  const ys: number[] = [];
  for (const e of elements) {
    if (e.type === "space" || e.type === "vertical") {
      xs.push(e.x ?? 0, (e.x ?? 0) + (e.width ?? 0));
      ys.push(e.y ?? 0, (e.y ?? 0) + (e.height ?? 0));
    }
    if (e.type === "wall") {
      xs.push(e.x1 ?? 0, e.x2 ?? 0);
      ys.push(e.y1 ?? 0, e.y2 ?? 0);
    }
  }
  if (xs.length === 0) return null;
  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const minY = Math.min(...ys);
  const maxY = Math.max(...ys);
  const span = Math.max(maxX - minX, maxY - minY, 1);
  const pad = span * 0.05;
  const stroke = span / 300;
  const sy = (y: number) => maxY - y; // SVG Y points down; the model's Y points up
  return (
    <svg
      role="img"
      aria-label="نمای طرح؛ عناصر را از جدول زیر انتخاب کنید"
      viewBox={`${minX - pad} ${-pad} ${maxX - minX + 2 * pad} ${maxY - minY + 2 * pad}`}
      style={{ width: "100%", maxHeight: "28rem" }}
      direction="ltr"
    >
      {elements.map((e) => {
        const chosen = e.id === selected;
        const common = { stroke: "currentColor", strokeWidth: stroke * (chosen ? 3 : 1), strokeDasharray: e.locked ? `${stroke * 4} ${stroke * 2}` : undefined };
        if (e.type === "space" || e.type === "vertical") {
          return (
            <g key={e.id} onClick={() => onPick(e.id)} style={{ cursor: "pointer" }}>
              <rect x={e.x} y={sy((e.y ?? 0) + (e.height ?? 0))} width={e.width} height={e.height} fill="currentColor" fillOpacity={chosen ? 0.3 : 0.1} {...common} />
              <text x={(e.x ?? 0) + (e.width ?? 0) / 2} y={sy((e.y ?? 0) + (e.height ?? 0) / 2)} textAnchor="middle" dominantBaseline="middle" fontSize={Math.max(span / 60, Math.min(e.width ?? 1, e.height ?? 1) / 5)} fill="currentColor">
                {e.id}
              </text>
            </g>
          );
        }
        if (e.type === "wall") {
          return <line key={e.id} x1={e.x1} y1={sy(e.y1 ?? 0)} x2={e.x2} y2={sy(e.y2 ?? 0)} onClick={() => onPick(e.id)} style={{ cursor: "pointer" }} {...common} strokeWidth={Math.max(e.thickness_m ?? 0.2, stroke) * (chosen ? 1.6 : 1)} />;
        }
        const wall = walls.get(e.wall_id ?? "");
        if (!wall) return null;
        const length = wallLength(wall);
        const ux = ((wall.x2 ?? 0) - (wall.x1 ?? 0)) / length;
        const uy = ((wall.y2 ?? 0) - (wall.y1 ?? 0)) / length;
        const a = [(wall.x1 ?? 0) + ux * (e.offset_m ?? 0), (wall.y1 ?? 0) + uy * (e.offset_m ?? 0)];
        const b = [a[0] + ux * (e.width_m ?? 0), a[1] + uy * (e.width_m ?? 0)];
        return <line key={e.id} x1={a[0]} y1={sy(a[1])} x2={b[0]} y2={sy(b[1])} onClick={() => onPick(e.id)} style={{ cursor: "pointer" }} stroke="Canvas" strokeWidth={Math.max(wall.thickness_m ?? 0.2, stroke) * 1.2} strokeDasharray={e.type === "window" ? `${stroke * 3} ${stroke * 2}` : undefined} />;
      })}
    </svg>
  );
}

export function DesignPanel({ projectId, canEdit, version }: { projectId: string; canEdit: boolean; version: number }) {
  const [reload, setReload] = useState(0);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<{ kind: "ok" | "error"; text: string } | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [floor, setFloor] = useState(1);
  const [alternativeId, setAlternativeId] = useState("");
  const [replace, setReplace] = useState(false);
  const [unit, setUnit] = useState<LengthUnit>("m");
  const [snap, setSnap] = useState("");
  const [aiText, setAiText] = useState("");
  const [proposal, setProposal] = useState<AiProposal | null>(null);
  const [aiBusy, setAiBusy] = useState(false);
  const resource = useResource<DesignState>(`/projects/${projectId}/design`, version + reload);
  const aiStatus = useResource<AiStatus>(`/projects/${projectId}/design/ai-status`, version);
  const historyState = useResource<DesignHistory>(`/projects/${projectId}/design/history`, version + reload);
  const layouts = useResource<LayoutState>(`/projects/${projectId}/layouts`, version + reload);
  const state = resource.data;
  const model = state?.data ?? null;
  const floors = model ? [...new Set(model.elements.map((e) => e.floor))].sort((a, b) => a - b) : [];
  const activeFloor = floors.includes(floor) ? floor : (floors[0] ?? 1);
  const elements = model?.elements.filter((e) => e.floor === activeFloor) ?? [];
  const current = model?.elements.find((e) => e.id === selected) ?? null;
  const factor = unitFactors[unit];
  const unitName = unitNames[unit];
  const scaled = (value: number | undefined) => Number(((value ?? 0) * factor).toFixed(3));
  const show = (value: number | undefined) => fa(scaled(value));
  const options = layouts.data?.data?.alternatives ?? [];
  const chosenAlternative = alternativeId || options[0]?.id || "";

  async function call(path: string, body: Record<string, unknown>, success: string) {
    setBusy(true);
    setMessage(null);
    try {
      await api.post(`/projects/${projectId}/design/${path}`, body);
      setMessage({ kind: "ok", text: success });
    } catch (error) {
      setMessage({ kind: "error", text: toApiError(error).userMessage });
    } finally {
      setBusy(false);
      setReload((value) => value + 1);
    }
  }

  const edit = (operation: DesignOperation, success = "تغییر ذخیره شد.") => {
    if (!state) return Promise.resolve();
    const body: Record<string, unknown> = { version: state.version, operations: [operation] };
    if (unit !== "m") body.unit = unit;
    if (snap) body.snap = { grid: Number(snap), unit };
    return call("edit", body, success);
  };

  async function askClaude() {
    setAiBusy(true);
    setMessage(null);
    setProposal(null);
    try {
      setProposal(await api.post<AiProposal>(`/projects/${projectId}/design/ai-proposal`, { instruction: aiText }));
    } catch (error) {
      setMessage({ kind: "error", text: toApiError(error).userMessage });
    } finally {
      setAiBusy(false);
    }
  }

  async function applyProposal() {
    if (!proposal) return;
    await call("edit", { version: proposal.base_version, operations: proposal.operations }, "پیشنهاد Claude اعمال شد؛ با «واگرد» می‌توانید برش گردانید.");
    setProposal(null);
  }

  const step = (direction: "undo" | "redo") =>
    state ? call(direction, { version: state.version }, direction === "undo" ? "آخرین تغییر برگردانده شد." : "تغییر دوباره اعمال شد.") : Promise.resolve();

  function submit(handler: (form: FormData) => DesignOperation) {
    return (event: FormEvent<HTMLFormElement>) => {
      event.preventDefault();
      void edit(handler(new FormData(event.currentTarget)));
    };
  }

  return (
    <section className="detail-section" aria-labelledby="design-title">
      <h2 id="design-title">ویرایش طرح</h2>
      <p className="field-hint">
        مدل پایهٔ قابل‌ویرایش؛ ذخیره‌سازی همیشه به متر است و واحد نمایش و ورودی را می‌توانید تغییر دهید. هر عنصر شناسهٔ ثابت دارد و عنصر قفل‌شده هیچ ویرایشی نمی‌پذیرد مگر باز شدن قفل. همپوشانی و ضوابط در این مرحله بررسی نمی‌شود.
      </p>
      {resource.error ? <p className="alert alert-error" role="alert">{resource.error.userMessage}</p> : null}
      {message ? (
        <div role={message.kind === "ok" ? "status" : "alert"} className={`alert alert-${message.kind === "ok" ? "success" : "error"}`}>
          {message.text}
        </div>
      ) : null}
      {state?.layout_changed ? (
        <p className="alert alert-error" role="alert">گزینه‌های چیدمان پس از وارد کردن این طرح تغییر کرده‌اند؛ طرح فعلی همان نسخهٔ قبلی را دارد.</p>
      ) : null}

      {canEdit && state ? (
        <form
          onSubmit={(event) => {
            event.preventDefault();
            void call("import-layout", { alternative_id: chosenAlternative, version: state.version, replace }, "گزینهٔ چیدمان به‌عنوان طرح وارد شد.");
          }}
        >
          <label>
            گزینهٔ چیدمان
            <select value={chosenAlternative} onChange={(event) => setAlternativeId(event.target.value)} disabled={options.length === 0}>
              {options.map((item) => (
                <option key={item.id} value={item.id}>{item.id}</option>
              ))}
            </select>
          </label>
          {model && model.elements.length > 0 ? (
            <label>
              <input type="checkbox" checked={replace} onChange={(event) => setReplace(event.target.checked)} /> جایگزینی طرح فعلی (ویرایش‌ها از بین می‌روند)
            </label>
          ) : null}
          <button className="button" type="submit" disabled={busy || !chosenAlternative}>
            واردکردن گزینه به‌عنوان طرح
          </button>
        </form>
      ) : state ? (
        <p className="field-hint">فقط مالک و معمار پروژه می‌توانند طرح را ویرایش کنند.</p>
      ) : resource.loading ? (
        <p className="status-text" role="status">در حال بارگذاری…</p>
      ) : null}

      {model && model.elements.length > 0 ? (
        <>
          {floors.length > 1 ? (
            <div className="tabs" role="group" aria-label="طبقه‌های طرح">
              {floors.map((item) => (
                <button key={item} type="button" className="tab" aria-pressed={item === activeFloor} onClick={() => setFloor(item)}>
                  طبقهٔ {fa(item)}
                </button>
              ))}
            </div>
          ) : null}
          {canEdit ? (
            <fieldset disabled={busy}>
              <legend>واحد، اسنپ و تاریخچه</legend>
              <label>
                واحد طول
                <select value={unit} onChange={(event) => { setUnit(event.target.value as LengthUnit); setSnap(""); }}>
                  {(Object.keys(unitNames) as LengthUnit[]).map((item) => <option key={item} value={item}>{unitNames[item]}</option>)}
                </select>
              </label>
              <label>
                اسنپ به شبکه
                <select value={snap} onChange={(event) => setSnap(event.target.value)}>
                  <option value="">بدون اسنپ</option>
                  {snapChoices[unit].map((item) => <option key={item} value={String(item)}>{fa(item)} {unitName}</option>)}
                </select>
              </label>
              <button type="button" className="button button-secondary" disabled={!state?.can_undo} onClick={() => void step("undo")}>واگرد</button>
              <button type="button" className="button button-secondary" disabled={!state?.can_redo} onClick={() => void step("redo")}>بازگردانی</button>
            </fieldset>
          ) : (
            <label>
              واحد نمایش
              <select value={unit} onChange={(event) => setUnit(event.target.value as LengthUnit)}>
                {(Object.keys(unitNames) as LengthUnit[]).map((item) => <option key={item} value={item}>{unitNames[item]}</option>)}
              </select>
            </label>
          )}
          <Drawing elements={elements} selected={selected} onPick={setSelected} />
          <div className="table-wrap">
            <table>
              <caption className="visually-hidden">عناصر طرح</caption>
              <thead>
                <tr><th scope="col">عنصر</th><th scope="col">مشخصات ({unitName})</th><th scope="col">قفل</th><th scope="col"><span className="visually-hidden">انتخاب</span></th></tr>
              </thead>
              <tbody>
                {elements.map((e) => (
                  <tr key={e.id}>
                    <td>{describe(e)}{e.id === selected ? " (منتخب)" : ""}</td>
                    <td>
                      {e.type === "space" || e.type === "vertical" ? `${show(e.x)}, ${show(e.y)} — ${show(e.width)}×${show(e.height)}` : null}
                      {e.type === "vertical" ? ` — طبقه‌های ${(e.floors ?? []).map(fa).join("، ")}` : null}
                      {e.type === "wall" ? `طول ${show(wallLength(e))}، ضخامت ${show(e.thickness_m)}` : null}
                      {e.wall_id ? `روی ${e.wall_id}، فاصله ${show(e.offset_m)}، عرض ${show(e.width_m)}` : null}
                    </td>
                    <td>{e.locked ? "قفل" : "آزاد"}</td>
                    <td><button type="button" className="button button-secondary" onClick={() => setSelected(e.id)}>انتخاب {e.id}</button></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {canEdit && current ? (
            <fieldset key={`${current.id}-${state?.version}-${unit}`} disabled={busy}>
              <legend>ویرایش {describe(current)} {current.locked ? "(قفل)" : ""}</legend>
              <button type="button" className="button button-secondary" onClick={() => void edit({ op: current.locked ? "unlock" : "lock", id: current.id }, current.locked ? "قفل باز شد." : "عنصر قفل شد.")}>
                {current.locked ? "باز کردن قفل" : "قفل کردن"}
              </button>
              {current.type === "space" || current.type === "vertical" || current.type === "wall" ? (
                <form onSubmit={submit((f) => ({ op: "move", id: current.id, dx: num(f, "dx"), dy: num(f, "dy") }))}>
                  <label>جابه‌جایی X ({unitName})<input name="dx" type="number" step="any" defaultValue={0} required /></label>
                  <label>جابه‌جایی Y ({unitName})<input name="dy" type="number" step="any" defaultValue={0} required /></label>
                  <button className="button" type="submit">جابه‌جایی</button>
                </form>
              ) : (
                <form onSubmit={submit((f) => ({ op: "move", id: current.id, along_m: num(f, "along") }))}>
                  <label>جابه‌جایی در امتداد دیوار ({unitName})<input name="along" type="number" step="any" defaultValue={0} required /></label>
                  <button className="button" type="submit">جابه‌جایی</button>
                </form>
              )}
              {current.type === "space" || current.type === "vertical" ? (
                <form onSubmit={submit((f) => ({ op: "resize", id: current.id, width: num(f, "width"), height: num(f, "height") }))}>
                  <label>عرض ({unitName})<input name="width" type="number" step="any" min="0" defaultValue={scaled(current.width)} required /></label>
                  <label>ارتفاع ({unitName})<input name="height" type="number" step="any" min="0" defaultValue={scaled(current.height)} required /></label>
                  <button className="button" type="submit">تغییر اندازه</button>
                </form>
              ) : null}
              {current.type === "wall" ? (
                <form onSubmit={submit((f) => ({ op: "resize", id: current.id, length_m: num(f, "length") }))}>
                  <label>طول ({unitName})<input name="length" type="number" step="any" min="0" defaultValue={scaled(wallLength(current))} required /></label>
                  <button className="button" type="submit">تغییر طول</button>
                </form>
              ) : null}
              {current.type === "door" || current.type === "window" || current.type === "opening" ? (
                <form onSubmit={submit((f) => ({ op: "resize", id: current.id, width_m: num(f, "openingWidth") }))}>
                  <label>عرض ({unitName})<input name="openingWidth" type="number" step="any" min="0" defaultValue={scaled(current.width_m)} required /></label>
                  <button className="button" type="submit">تغییر عرض</button>
                </form>
              ) : null}
              {current.type === "space" || current.type === "vertical" ? (
                <button type="button" className="button button-secondary" onClick={() => void edit({ op: "rotate", id: current.id, degrees: 90 }, "فضا ۹۰ درجه چرخید.")}>چرخش ۹۰ درجه</button>
              ) : null}
              {current.type === "wall" ? (
                <form onSubmit={submit((f) => ({ op: "rotate", id: current.id, degrees: num(f, "degrees") }))}>
                  <label>چرخش حول وسط دیوار (درجه)<input name="degrees" type="number" step="any" defaultValue={90} required /></label>
                  <button className="button" type="submit">چرخاندن</button>
                </form>
              ) : null}
              {current.type === "vertical" ? (
                <form onSubmit={submit((f) => ({ op: "set_floors", id: current.id, floors: String(f.get("levels")).split(/[,،\s]+/).filter(Boolean).map(Number) }))}>
                  <label>طبقه‌های متصل (با ویرگول جدا کنید)<input name="levels" defaultValue={(current.floors ?? []).join(",")} required /></label>
                  <button className="button" type="submit">ذخیرهٔ طبقه‌ها</button>
                </form>
              ) : null}
              <button type="button" className="button button-secondary" onClick={() => void edit({ op: "delete", id: current.id }, "عنصر حذف شد.")}>
                حذف {current.id}
              </button>
            </fieldset>
          ) : null}

          {canEdit ? (
            <fieldset disabled={busy}>
              <legend key={unit}>افزودن عنصر</legend>
              <form onSubmit={submit((f) => ({ op: "add", element: { type: "space", floor: activeFloor, kind: String(f.get("kind")), x: num(f, "sx"), y: num(f, "sy"), width: num(f, "sw"), height: num(f, "sh") } }))}>
                <label>نوع فضا<select name="kind">{kindChoices.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}</select></label>
                <label>X<input name="sx" type="number" step="any" defaultValue={0} required /></label>
                <label>Y<input name="sy" type="number" step="any" defaultValue={0} required /></label>
                <label>عرض ({unitName})<input name="sw" type="number" step="any" min="0" defaultValue={scaled(3)} required /></label>
                <label>ارتفاع ({unitName})<input name="sh" type="number" step="any" min="0" defaultValue={scaled(3)} required /></label>
                <button className="button" type="submit">افزودن فضا</button>
              </form>
              <form onSubmit={submit((f) => ({ op: "add", element: { type: "wall", floor: activeFloor, x1: num(f, "x1"), y1: num(f, "y1"), x2: num(f, "x2"), y2: num(f, "y2"), thickness_m: num(f, "thickness") } }))}>
                <label>X۱<input name="x1" type="number" step="any" defaultValue={0} required /></label>
                <label>Y۱<input name="y1" type="number" step="any" defaultValue={0} required /></label>
                <label>X۲<input name="x2" type="number" step="any" defaultValue={scaled(3)} required /></label>
                <label>Y۲<input name="y2" type="number" step="any" defaultValue={0} required /></label>
                <label>ضخامت ({unitName})<input name="thickness" type="number" step="any" min="0" defaultValue={scaled(0.2)} required /></label>
                <button className="button" type="submit">افزودن دیوار</button>
              </form>
              <form onSubmit={submit((f) => ({ op: "copy_floor", from_floor: activeFloor, to_floors: String(f.get("targets")).split(/[,،\s]+/).filter(Boolean).map(Number) }))}>
                <label>کپی طبقهٔ {fa(activeFloor)} روی طبقه‌های (با ویرگول جدا کنید)<input name="targets" inputMode="numeric" defaultValue={String(activeFloor + 1)} required /></label>
                <button className="button" type="submit">کپی طبقه</button>
              </form>
              <form onSubmit={submit((f) => ({ op: "add", element: { type: "vertical", kind: String(f.get("vkind")), floors: String(f.get("vfloors")).split(/[,،\s]+/).filter(Boolean).map(Number), x: num(f, "vx"), y: num(f, "vy"), width: num(f, "vw"), height: num(f, "vh") } }))}>
                <label>نوع ارتباط عمودی<select name="vkind">{Object.entries(verticalKinds).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
                <label>طبقه‌های متصل<input name="vfloors" defaultValue={`${activeFloor},${activeFloor + 1}`} required /></label>
                <label>X ({unitName})<input name="vx" type="number" step="any" defaultValue={0} required /></label>
                <label>Y ({unitName})<input name="vy" type="number" step="any" defaultValue={0} required /></label>
                <label>عرض ({unitName})<input name="vw" type="number" step="any" min="0" defaultValue={scaled(1.2)} required /></label>
                <label>ارتفاع ({unitName})<input name="vh" type="number" step="any" min="0" defaultValue={scaled(3)} required /></label>
                <button className="button" type="submit">افزودن ارتباط عمودی</button>
              </form>
              <form onSubmit={submit((f) => ({ op: "add", element: { type: String(f.get("hosted")), wall_id: String(f.get("wall")), offset_m: num(f, "offset"), width_m: num(f, "hwidth") } }))}>
                <label>نوع<select name="hosted"><option value="door">در</option><option value="window">پنجره</option><option value="opening">بازشو</option></select></label>
                <label>دیوار<select name="wall">{elements.filter((e) => e.type === "wall").map((w) => <option key={w.id} value={w.id}>{w.id}</option>)}</select></label>
                <label>فاصله از ابتدای دیوار ({unitName})<input name="offset" type="number" step="any" min="0" defaultValue={scaled(0.5)} required /></label>
                <label>عرض ({unitName})<input name="hwidth" type="number" step="any" min="0" defaultValue={scaled(0.9)} required /></label>
                <button className="button" type="submit">افزودن به دیوار</button>
              </form>
            </fieldset>
          ) : null}

          {canEdit && state?.exists ? (
            <fieldset disabled={busy || aiBusy}>
              <legend>پیشنهاد طراحی با Claude</legend>
              {aiStatus.data && !aiStatus.data.enabled ? (
                <p className="field-hint">
                  Claude هنوز روی این سرور فعال نیست. کلید API را فقط روی سرور و در متغیر SMART_ENGINEER_ANTHROPIC_API_KEY بگذارید (نه در چت و نه در مخزن) و API را دوباره اجرا کنید.
                </p>
              ) : (
                <>
                  <p className="field-hint">
                    Claude فهرستی از تغییرات پیشنهاد می‌دهد؛ چیزی خودکار تغییر نمی‌کند. پیشنهاد پیش از نمایش با قواعد طرح (قفل‌ها، شناسه‌ها، محدودیت‌ها) آزمایش می‌شود و با دکمهٔ «اعمال» روی طرح می‌نشیند. هر درخواست هزینهٔ API دارد و نتیجه نقشهٔ تأییدشدهٔ مهندسی نیست.
                  </p>
                  <label>
                    درخواست شما (اختیاری)
                    <textarea value={aiText} maxLength={1000} onChange={(event) => setAiText(event.target.value)} />
                  </label>
                  <button type="button" className="button" disabled={!aiStatus.data?.enabled} onClick={() => void askClaude()}>
                    {aiBusy ? "در حال دریافت پیشنهاد…" : "دریافت پیشنهاد از Claude"}
                  </button>
                </>
              )}
            </fieldset>
          ) : null}
          {proposal ? (
            <div aria-live="polite">
              <h3>پیشنهاد Claude</h3>
              <p>{proposal.summary || "بدون توضیح."}</p>
              {proposal.valid ? (
                <p role="status">{fa(proposal.operations.length)} تغییر پیشنهاد شد و با قواعد طرح سازگار است.</p>
              ) : (
                <p role="alert" className="alert alert-error">
                  پیشنهاد با قواعد طرح سازگار نیست: {messageForCode(proposal.error?.code ?? "")}
                  {proposal.error?.element_id ? ` (${proposal.error.element_id})` : ""}
                </p>
              )}
              {proposal.operations.length > 0 ? (
                <ol className="flag-list">
                  {proposal.operations.map((item, index) => (
                    <li key={index}>{operationLabels[String(item.op)] ?? String(item.op)}{typeof item.id === "string" ? ` ${item.id}` : ""}</li>
                  ))}
                </ol>
              ) : null}
              {proposal.base_version !== state?.version ? (
                <p className="alert alert-error" role="alert">طرح پس از این پیشنهاد تغییر کرده است؛ پیشنهاد جدید بگیرید.</p>
              ) : null}
              <button
                type="button"
                className="button"
                disabled={busy || !proposal.valid || proposal.operations.length === 0 || proposal.base_version !== state?.version}
                onClick={() => void applyProposal()}
              >
                اعمال پیشنهاد
              </button>
              <button type="button" className="button button-secondary" onClick={() => setProposal(null)}>کنار گذاشتن</button>
            </div>
          ) : null}

          {historyState.data && historyState.data.entries.length > 0 ? (
            <details>
              <summary>تاریخچهٔ تغییرات</summary>
              <ol className="flag-list" reversed>
                {historyState.data.entries.map((entry) => (
                  <li key={entry.seq}>
                    {entry.summary.action === "import"
                      ? "وارد کردن گزینهٔ چیدمان"
                      : (entry.summary.operations ?? []).map((item) => `${operationLabels[item.op] ?? item.op}${item.id ? ` ${item.id}` : ""}`).join("، ")}
                    {" — "}{entry.actor}{entry.current ? " (وضعیت فعلی)" : ""}
                  </li>
                ))}
              </ol>
            </details>
          ) : null}
        </>
      ) : null}
    </section>
  );
}
