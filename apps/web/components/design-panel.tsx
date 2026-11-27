"use client";

import { useState, type FormEvent } from "react";

import { api, toApiError } from "../lib/api";
import { typeLabels, wallLength, type DesignElement, type DesignOperation, type DesignState } from "../lib/design";
import type { LayoutState } from "../lib/layouts";
import { requirementSections } from "../lib/requirements";
import { useResource } from "../lib/use-resource";

const kindChoices = (requirementSections[0].lists?.[0]?.columns ?? [])
  .filter((column) => column.name === "kind")
  .flatMap((column) => column.choices ?? []);
const kindLabels: Record<string, string> = Object.fromEntries(kindChoices.map((c) => [c.value, c.label]));

const fa = (value: number) => value.toLocaleString("fa-IR", { maximumFractionDigits: 3 });
const num = (form: FormData, name: string) => Number(form.get(name));

function describe(element: DesignElement): string {
  const base = `${element.id} — ${typeLabels[element.type]}`;
  if (element.type === "space") return `${base} ${element.name ?? kindLabels[element.kind ?? ""] ?? element.kind ?? ""}`;
  return element.label ? `${base} ${element.label}` : base;
}

function Drawing({ elements, selected, onPick }: { elements: DesignElement[]; selected: string | null; onPick: (id: string) => void }) {
  const walls = new Map(elements.filter((e) => e.type === "wall").map((w) => [w.id, w]));
  const xs: number[] = [];
  const ys: number[] = [];
  for (const e of elements) {
    if (e.type === "space") {
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
        if (e.type === "space") {
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
  const resource = useResource<DesignState>(`/projects/${projectId}/design`, version + reload);
  const layouts = useResource<LayoutState>(`/projects/${projectId}/layouts`, version + reload);
  const state = resource.data;
  const model = state?.data ?? null;
  const floors = model ? [...new Set(model.elements.map((e) => e.floor))].sort((a, b) => a - b) : [];
  const activeFloor = floors.includes(floor) ? floor : (floors[0] ?? 1);
  const elements = model?.elements.filter((e) => e.floor === activeFloor) ?? [];
  const current = model?.elements.find((e) => e.id === selected) ?? null;
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

  const edit = (operation: DesignOperation, success = "تغییر ذخیره شد.") =>
    state ? call("edit", { version: state.version, operations: [operation] }, success) : Promise.resolve();

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
        مدل پایهٔ قابل‌ویرایش (متر). هر عنصر شناسهٔ ثابت دارد و عنصر قفل‌شده هیچ ویرایشی نمی‌پذیرد مگر باز شدن قفل. همپوشانی و ضوابط در این مرحله بررسی نمی‌شود.
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
          <Drawing elements={elements} selected={selected} onPick={setSelected} />
          <div className="table-wrap">
            <table>
              <caption className="visually-hidden">عناصر طرح</caption>
              <thead>
                <tr><th scope="col">عنصر</th><th scope="col">مشخصات (متر)</th><th scope="col">قفل</th><th scope="col"><span className="visually-hidden">انتخاب</span></th></tr>
              </thead>
              <tbody>
                {elements.map((e) => (
                  <tr key={e.id}>
                    <td>{describe(e)}{e.id === selected ? " (منتخب)" : ""}</td>
                    <td>
                      {e.type === "space" ? `${fa(e.x ?? 0)}, ${fa(e.y ?? 0)} — ${fa(e.width ?? 0)}×${fa(e.height ?? 0)}` : null}
                      {e.type === "wall" ? `طول ${fa(wallLength(e))}، ضخامت ${fa(e.thickness_m ?? 0)}` : null}
                      {e.wall_id ? `روی ${e.wall_id}، فاصله ${fa(e.offset_m ?? 0)}، عرض ${fa(e.width_m ?? 0)}` : null}
                    </td>
                    <td>{e.locked ? "قفل" : "آزاد"}</td>
                    <td><button type="button" className="button button-secondary" onClick={() => setSelected(e.id)}>انتخاب {e.id}</button></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {canEdit && current ? (
            <fieldset key={`${current.id}-${state?.version}`} disabled={busy}>
              <legend>ویرایش {describe(current)} {current.locked ? "(قفل)" : ""}</legend>
              <button type="button" className="button button-secondary" onClick={() => void edit({ op: current.locked ? "unlock" : "lock", id: current.id }, current.locked ? "قفل باز شد." : "عنصر قفل شد.")}>
                {current.locked ? "باز کردن قفل" : "قفل کردن"}
              </button>
              {current.type === "space" || current.type === "wall" ? (
                <form onSubmit={submit((f) => ({ op: "move", id: current.id, dx: num(f, "dx"), dy: num(f, "dy") }))}>
                  <label>جابه‌جایی X (متر)<input name="dx" type="number" step="any" defaultValue={0} required /></label>
                  <label>جابه‌جایی Y (متر)<input name="dy" type="number" step="any" defaultValue={0} required /></label>
                  <button className="button" type="submit">جابه‌جایی</button>
                </form>
              ) : (
                <form onSubmit={submit((f) => ({ op: "move", id: current.id, along_m: num(f, "along") }))}>
                  <label>جابه‌جایی در امتداد دیوار (متر)<input name="along" type="number" step="any" defaultValue={0} required /></label>
                  <button className="button" type="submit">جابه‌جایی</button>
                </form>
              )}
              {current.type === "space" ? (
                <form onSubmit={submit((f) => ({ op: "resize", id: current.id, width: num(f, "width"), height: num(f, "height") }))}>
                  <label>عرض (متر)<input name="width" type="number" step="any" min="0" defaultValue={current.width} required /></label>
                  <label>ارتفاع (متر)<input name="height" type="number" step="any" min="0" defaultValue={current.height} required /></label>
                  <button className="button" type="submit">تغییر اندازه</button>
                </form>
              ) : null}
              {current.type === "wall" ? (
                <form onSubmit={submit((f) => ({ op: "resize", id: current.id, length_m: num(f, "length") }))}>
                  <label>طول (متر)<input name="length" type="number" step="any" min="0" defaultValue={Number(wallLength(current).toFixed(3))} required /></label>
                  <button className="button" type="submit">تغییر طول</button>
                </form>
              ) : null}
              {current.type === "door" || current.type === "window" || current.type === "opening" ? (
                <form onSubmit={submit((f) => ({ op: "resize", id: current.id, width_m: num(f, "openingWidth") }))}>
                  <label>عرض (متر)<input name="openingWidth" type="number" step="any" min="0" defaultValue={current.width_m} required /></label>
                  <button className="button" type="submit">تغییر عرض</button>
                </form>
              ) : null}
              {current.type === "space" ? (
                <button type="button" className="button button-secondary" onClick={() => void edit({ op: "rotate", id: current.id, degrees: 90 }, "فضا ۹۰ درجه چرخید.")}>چرخش ۹۰ درجه</button>
              ) : null}
              {current.type === "wall" ? (
                <form onSubmit={submit((f) => ({ op: "rotate", id: current.id, degrees: num(f, "degrees") }))}>
                  <label>چرخش حول وسط دیوار (درجه)<input name="degrees" type="number" step="any" defaultValue={90} required /></label>
                  <button className="button" type="submit">چرخاندن</button>
                </form>
              ) : null}
              <button type="button" className="button button-secondary" onClick={() => void edit({ op: "delete", id: current.id }, "عنصر حذف شد.")}>
                حذف {current.id}
              </button>
            </fieldset>
          ) : null}

          {canEdit ? (
            <fieldset disabled={busy}>
              <legend>افزودن عنصر</legend>
              <form onSubmit={submit((f) => ({ op: "add", element: { type: "space", floor: activeFloor, kind: String(f.get("kind")), x: num(f, "sx"), y: num(f, "sy"), width: num(f, "sw"), height: num(f, "sh") } }))}>
                <label>نوع فضا<select name="kind">{kindChoices.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}</select></label>
                <label>X<input name="sx" type="number" step="any" defaultValue={0} required /></label>
                <label>Y<input name="sy" type="number" step="any" defaultValue={0} required /></label>
                <label>عرض<input name="sw" type="number" step="any" min="0" defaultValue={3} required /></label>
                <label>ارتفاع<input name="sh" type="number" step="any" min="0" defaultValue={3} required /></label>
                <button className="button" type="submit">افزودن فضا</button>
              </form>
              <form onSubmit={submit((f) => ({ op: "add", element: { type: "wall", floor: activeFloor, x1: num(f, "x1"), y1: num(f, "y1"), x2: num(f, "x2"), y2: num(f, "y2"), thickness_m: num(f, "thickness") } }))}>
                <label>X۱<input name="x1" type="number" step="any" defaultValue={0} required /></label>
                <label>Y۱<input name="y1" type="number" step="any" defaultValue={0} required /></label>
                <label>X۲<input name="x2" type="number" step="any" defaultValue={3} required /></label>
                <label>Y۲<input name="y2" type="number" step="any" defaultValue={0} required /></label>
                <label>ضخامت (متر)<input name="thickness" type="number" step="any" min="0" defaultValue={0.2} required /></label>
                <button className="button" type="submit">افزودن دیوار</button>
              </form>
              <form onSubmit={submit((f) => ({ op: "add", element: { type: String(f.get("hosted")), wall_id: String(f.get("wall")), offset_m: num(f, "offset"), width_m: num(f, "hwidth") } }))}>
                <label>نوع<select name="hosted"><option value="door">در</option><option value="window">پنجره</option><option value="opening">بازشو</option></select></label>
                <label>دیوار<select name="wall">{elements.filter((e) => e.type === "wall").map((w) => <option key={w.id} value={w.id}>{w.id}</option>)}</select></label>
                <label>فاصله از ابتدای دیوار (متر)<input name="offset" type="number" step="any" min="0" defaultValue={0.5} required /></label>
                <label>عرض (متر)<input name="hwidth" type="number" step="any" min="0" defaultValue={0.9} required /></label>
                <button className="button" type="submit">افزودن به دیوار</button>
              </form>
            </fieldset>
          ) : null}
        </>
      ) : null}
    </section>
  );
}
