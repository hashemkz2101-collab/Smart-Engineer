"use client";

import { useEffect, useRef, useState, type PointerEvent } from "react";

import { api, toApiError } from "../lib/api";
import {
  geometryNumber, geometryReasons, readBoundary, roleLabels, unitFactors, viewBounds,
  type EdgeAssignment, type EdgeRole, type GeometryReport, type Unit, type Vertex,
} from "../lib/geometry";

const pathOf = (points: [number, number][]) =>
  points.length ? `M${points.map(([x, y]) => `${x},${-y}`).join("L")}Z` : "";

export function GeometryEditor({
  projectId, data, canEdit, disabled = false, onChange, onCanonical,
}: {
  projectId: string;
  data: Record<string, unknown>;
  canEdit: boolean;
  disabled?: boolean;
  onChange: (data: Record<string, unknown>) => void;
  onCanonical: (key: string, data: Record<string, unknown>) => void;
}) {
  const editable = canEdit && !disabled;
  const points = readBoundary(data);
  const empty = !data.shape && points.length === 0;
  const finite = points.every((p) => Number.isFinite(p.x) && Number.isFinite(p.y));
  const [unit, setUnit] = useState<Unit>("m");
  const [selected, setSelected] = useState(0);
  const [drawing, setDrawing] = useState(false);
  const [snap, setSnap] = useState(false);
  const [step, setStep] = useState("1");
  const [view, setView] = useState(() => viewBounds(points));
  const [response, setResponse] = useState<{ key: string; report?: GeometryReport; errors?: string[] } | null>(null);
  const svg = useRef<SVGSVGElement>(null);
  const [canvasSize, setCanvasSize] = useState(650);
  useEffect(() => {
    if (!svg.current) return;
    const observer = new ResizeObserver(([entry]) => {
      setCanvasSize(Math.max(1, Math.min(entry.contentRect.width, entry.contentRect.height)));
    });
    observer.observe(svg.current);
    return () => observer.disconnect();
  }, []);
  const dragging = useRef<number | null>(null);
  const canonicalCallback = useRef(onCanonical);
  useEffect(() => { canonicalCallback.current = onCanonical; }, [onCanonical]);
  const key = JSON.stringify(data);
  useEffect(() => {
    if (!JSON.parse(key).shape) return;
    let active = true;
    const timer = setTimeout(() => {
      const request = canEdit
        ? api.post<GeometryReport>(`/projects/${projectId}/geometry/preview`, { data: JSON.parse(key), unit: "m" })
        : api.get<GeometryReport>(`/projects/${projectId}/geometry`);
      request.then((report) => {
        if (!active) return;
        setResponse({ key, report });
        if (report.canonical_data) canonicalCallback.current(key, report.canonical_data);
      }, (failure: unknown) => {
        if (!active) return;
        const error = toApiError(failure);
        const reasons = error.details.map((d) => {
          const detail = d as { reason?: string; field?: string };
          return `${detail.field ?? ""}: ${geometryReasons[detail.reason ?? ""] ?? "ورودی را بررسی کنید."}`;
        });
        setResponse({ key, errors: reasons.length ? reasons : [error.userMessage] });
      });
    }, 450);
    return () => { active = false; clearTimeout(timer); };
  }, [key, projectId, canEdit]);

  const current = response?.key === key ? response : null;
  const report = current?.report;
  const index = Math.min(selected, Math.max(points.length - 1, 0));
  const factor = unitFactors[unit];
  const increment = Number(step) > 0 && Number.isFinite(Number(step)) ? Number(step) * factor : factor;
  const scale = view.width / canvasSize;
  const mappings = ((Array.isArray(data.setback_edges) ? data.setback_edges : []) as EdgeAssignment[])
    .map((m) => ({ edge_index: Number(m.edge_index), role: m.role }));
  const safePoints = finite ? points : [];

  function changePoints(next: Vertex[], topology = false) {
    onChange({ ...data, shape: "polygon", vertices: next, geometry_reference: "local_cartesian",
      setback_edges: topology ? [] : mappings });
  }
  function move(at: number, point: Vertex) {
    const next = { x: point.x, y: point.y };
    if (snap) {
      next.x = Math.round(next.x / increment) * increment;
      next.y = Math.round(next.y / increment) * increment;
    }
    changePoints(points.map((p, i) => i === at ? next : p));
  }
  function fromPointer(event: PointerEvent<SVGSVGElement>): Vertex | null {
    const matrix = svg.current?.getScreenCTM();
    if (!matrix || !svg.current) return null;
    const point = svg.current.createSVGPoint();
    point.x = event.clientX; point.y = event.clientY;
    const local = point.matrixTransform(matrix.inverse());
    return { x: local.x, y: -local.y };
  }
  function zoom(multiplier: number) {
    const width = Math.max(0.01, Math.min(1e8, view.width * multiplier));
    const height = width;
    setView({ x: view.x + (view.width - width) / 2, y: view.y + (view.height - height) / 2, width, height });
  }
  function assign(at: number, role: string) {
    const others = mappings.filter((m) => m.edge_index !== at);
    onChange({ ...data, setback_edges: role ? [...others, { edge_index: at, role: role as EdgeRole }] : others });
  }

  return (
    <section className="geometry-editor" aria-labelledby="geometry-title" data-testid="geometry-editor">
      <div className="geometry-heading">
        <div><h4 id="geometry-title">بوم زمین</h4><p className="field-hint">محور X به راست و Y به بالا؛ مختصات محلی، نه طول و عرض جغرافیایی.</p></div>
        <label className="geometry-unit">واحد نمایش
          <select aria-label="واحد نمایش بوم" value={unit} onChange={(e) => setUnit(e.target.value as Unit)}>
            <option value="m">متر</option><option value="cm">سانتی‌متر</option><option value="mm">میلی‌متر</option>
          </select>
        </label>
      </div>
      <div className="geometry-tools" role="group" aria-label="ابزارهای بوم زمین">
        {editable ? <>
          <button type="button" className="button button-secondary" onClick={() => {
            onChange({ ...data, shape: "rectangular", width_m: 10, depth_m: 20, vertices: [],
              geometry_reference: "local_cartesian", setback_edges: [] });
            setDrawing(false); setView(viewBounds([{ x: 0, y: 0 }, { x: 10, y: 20 }]));
          }}>ساخت مستطیل ۱۰×۲۰ متر</button>
          <button type="button" className="button button-secondary" aria-pressed={drawing} onClick={() => {
            if (!drawing) { changePoints([], true); setSelected(0); }
            setDrawing(!drawing);
          }}>{drawing ? "پایان رسم مرز" : "رسم مرز جدید"}</button>
          <button type="button" className="button button-secondary" disabled={points.length >= 200 || !finite}
            onClick={() => {
              const last = points.at(-1) ?? { x: 0, y: 0 };
              changePoints([...points, { x: last.x + increment, y: last.y + increment }], true);
              setSelected(points.length);
            }}>افزودن رأس</button>
          <button type="button" className="button button-secondary" disabled={points.length <= 3}
            onClick={() => { changePoints(points.filter((_, i) => i !== index), true); setSelected(Math.max(0, index - 1)); }}>حذف رأس انتخاب‌شده</button>
        </> : null}
        <button type="button" className="button button-secondary" onClick={() => zoom(0.75)} aria-label="بزرگ‌نمایی بوم">+</button>
        <button type="button" className="button button-secondary" onClick={() => zoom(1.33)} aria-label="کوچک‌نمایی بوم">−</button>
        <button type="button" className="button button-secondary" onClick={() => setView(viewBounds(points))}>نمایش کل زمین</button>
      </div>
      {editable ? <div className="geometry-settings">
        <label><input type="checkbox" checked={snap} onChange={(e) => setSnap(e.target.checked)} /> چسبیدن به شبکه</label>
        <label>گام شبکه و جابه‌جایی ({unit}) <input aria-label="گام شبکه" type="number" min="0.001" step="any" value={step} onChange={(e) => setStep(e.target.value)} /></label>
        <span className="field-hint">پیکان‌ها: جابه‌جایی رأس؛ Shift: ده گام. تغییر واحد، مرز ذخیره‌شده را عوض نمی‌کند.</span>
      </div> : null}
      {drawing ? <p role="status" className="alert alert-notice">برای افزودن رأس روی بوم بزنید. مرز جدید فقط پس از «ذخیرهٔ این بخش» ثبت می‌شود.</p> : null}
      <div className="geometry-workspace">
        <div className="geometry-sheet">
          <svg ref={svg} className="geometry-canvas" viewBox={`${view.x} ${-(view.y + view.height)} ${view.width} ${view.height}`}
            role="group" aria-label="بوم دوبعدی مرز زمین" aria-describedby="geometry-help"
            onPointerMove={(event) => {
              if (dragging.current === null || !editable) return;
              const p = fromPointer(event); if (p) move(dragging.current, p);
            }}
            onPointerUp={(event) => {
              if (dragging.current !== null) { dragging.current = null; event.currentTarget.releasePointerCapture(event.pointerId); }
            }}
            onPointerCancel={() => { dragging.current = null; }}
            onPointerDown={(event) => {
              if (!drawing || !editable || points.length >= 200) return;
              const p = fromPointer(event); if (p) changePoints([...points, p], true);
            }}>
            <defs>
              <pattern id="geometry-grid" width={increment} height={increment} patternUnits="userSpaceOnUse">
                <path d={`M ${increment} 0 L 0 0 0 ${increment}`} className="geometry-grid-line" strokeWidth={scale * 0.6} fill="none" />
              </pattern>
              <pattern id="geometry-envelope-hatch" width={scale * 10} height={scale * 10} patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
                <line x1="0" x2="0" y1="0" y2={scale * 10} stroke="currentColor" strokeWidth={scale * 2} />
              </pattern>
            </defs>
            <rect x={view.x} y={-(view.y + view.height)} width={view.width} height={view.height} fill="url(#geometry-grid)" />
            <path d={`M${view.x},0h${view.width} M0,${-view.y}v${-view.height}`} className="geometry-axis" strokeWidth={scale} />
            {safePoints.length ? <path data-testid="parcel-boundary" d={pathOf(safePoints.map((p) => [p.x, p.y]))} className="geometry-boundary" strokeWidth={scale * 2} /> : null}
            {report?.envelope?.polygons.map((piece, i) => <path key={i} data-testid="buildable-boundary"
              d={pathOf(piece.exterior) + piece.holes.map(pathOf).join("")} fillRule="evenodd"
              className="geometry-envelope" strokeWidth={scale * 2} />)}
            {safePoints.map((p, i) => <g key={i}>
              <circle cx={p.x} cy={-p.y} r={scale * (i === index ? 7 : 5)}
                className={`geometry-vertex ${i === index ? "is-selected" : ""}`}
                strokeWidth={scale * 2} role="button" aria-label={`رأس ${i + 1}`} tabIndex={editable ? 0 : -1}
                onFocus={() => setSelected(i)}
                onPointerDown={(event) => {
                  if (!editable || drawing) return;
                  event.stopPropagation(); setSelected(i); dragging.current = i;
                  svg.current?.setPointerCapture(event.pointerId);
                }}
                onKeyDown={(event) => {
                  if (!editable) return;
                  const directions: Record<string, [number, number]> = {
                    ArrowLeft: [-1, 0], ArrowRight: [1, 0], ArrowUp: [0, 1], ArrowDown: [0, -1],
                  };
                  const delta = directions[event.key];
                  if (!delta) return;
                  event.preventDefault(); const amount = increment * (event.shiftKey ? 10 : 1);
                  move(i, { x: p.x + delta[0] * amount, y: p.y + delta[1] * amount });
                }} />
              <text x={p.x + scale * 10} y={-p.y - scale * 10} fontSize={scale * 14} className="geometry-label">{i + 1}</text>
              {report?.edges?.[i] && safePoints.length > 1 ? <text
                x={(p.x + safePoints[(i + 1) % safePoints.length].x) / 2}
                y={-(p.y + safePoints[(i + 1) % safePoints.length].y) / 2 - scale * 9}
                textAnchor="middle" fontSize={scale * 12} className="geometry-label">
                {geometryNumber(report.edges[i].length_m / factor)} {unit}
              </text> : null}
            </g>)}
          </svg>
          {report?.north_angle_deg != null ? <span className="geometry-north" aria-label={`شمال با زاویه ${report.north_angle_deg} درجه`}>
            <span style={{ transform: `rotate(${report.north_angle_deg}deg)` }}>↑</span> شمال
          </span> : <span className="geometry-north">شمال ثبت نشده</span>}
          {!safePoints.length ? <p className="geometry-empty">از فرم ابعاد، ساخت مستطیل یا رسم مرز شروع کنید.</p> : null}
          <span className="geometry-axes" dir="ltr">X → · Y ↑ · {unit}</span>
        </div>
        <div className="geometry-inspector">
          <h5>رئوس و اضلاع</h5>
          <p id="geometry-help" className="field-hint">رأس را بکشید یا مختصات را ویرایش کنید. بعد از افزودن یا حذف رأس، نوع اضلاع را دوباره مشخص کنید.</p>
          <ol className="geometry-vertex-list">
            {points.map((p, i) => <li key={i} className={i === index ? "is-selected" : ""}>
              <button type="button" className="geometry-select" aria-pressed={i === index} onClick={() => setSelected(i)}>رأس {geometryNumber(i + 1, 0)}</button>
              <div className="geometry-coordinate-row" dir="ltr">
                {(["x", "y"] as const).map((axis) => <label key={axis}>{axis.toUpperCase()}
                  <input aria-label={`${axis.toUpperCase()} رأس ${i + 1} (${unit})`} type="number" step="any"
                    disabled={!editable} value={Number.isFinite(p[axis]) ? Number((p[axis] / factor).toPrecision(16)) : ""}
                    onChange={(event) => {
                      if (!event.target.value.trim()) return;
                      const value = Number(event.target.value) * factor;
                      if (Number.isFinite(value)) move(i, { ...p, [axis]: value });
                    }} />
                </label>)}
              </div>
              <label className="geometry-edge-role">ضلع {geometryNumber(i + 1)} به {geometryNumber((i + 1) % points.length + 1)}
                <select aria-label={`نوع ضلع ${i + 1}`} disabled={!editable}
                  value={mappings.find((m) => m.edge_index === i)?.role ?? ""}
                  onChange={(e) => assign(i, e.target.value)}>
                  <option value="">مشخص نشده</option>
                  {Object.entries(roleLabels).map(([value, text]) => <option key={value} value={value}>{text}</option>)}
                </select>
              </label>
            </li>)}
          </ol>
        </div>
      </div>
      <div className="geometry-report" aria-live="polite" data-testid="geometry-report">
        {empty ? <p>هنوز مرزی وارد نشده است؛ ابعاد مستطیل را وارد کنید یا یک مرز رسم کنید.</p> : null}
        {!empty && !current ? <p role="status">در حال بررسی هندسهٔ فعلی…</p> : null}
        {!empty && current?.errors ? <div className="alert alert-error" role="alert"><p>پیش‌نمایش قابل محاسبه نیست:</p><ul>{current.errors.map((message) => <li key={message}>{message}</li>)}</ul></div> : null}
        {report?.errors ? <ul className="field-error">{report.errors.map((e) => <li key={e.field}>{geometryReasons[e.reason] ?? e.reason}</li>)}</ul> : null}
        {report?.status === "valid" ? <>
          <dl className="geometry-results">
            <div><dt>مساحت زمین</dt><dd>{geometryNumber(report.area_m2 ?? 0)} متر مربع</dd></div>
            <div><dt>محیط زمین</dt><dd>{geometryNumber(report.perimeter_m ?? 0)} متر</dd></div>
            <div><dt>ترتیب رئوس</dt><dd>{report.orientation === "counterclockwise" ? "پادساعت‌گرد" : "ساعت‌گرد"}</dd></div>
            <div><dt>مساحت پس از عقب‌نشینی</dt><dd>{report.envelope?.area_m2 == null ? "نیازمند استعلام" : `${geometryNumber(report.envelope.area_m2)} متر مربع`}</dd></div>
          </dl>
          {report.area_status === "discrepancy" ? <p className="alert alert-notice">اختلاف با مساحت اظهارشده: {geometryNumber(report.difference_m2 ?? 0)} متر مربع ({geometryNumber(report.difference_percent ?? 0)}٪)؛ نیازمند بررسی است.</p> : null}
          {report.envelope?.status === "empty" ? <p className="alert alert-notice">عقب‌نشینی‌های ثبت‌شده تمام زمین را حذف می‌کنند؛ محدودهٔ قابل ساخت خالی است.</p> : null}
          {report.envelope?.status === "needs_inquiry" ? <details className="geometry-inquiry"><summary>برای محاسبهٔ محدودهٔ قابل ساخت چه چیزی لازم است؟</summary>
            <ul>{report.envelope.reasons.map((reason) => <li key={reason}>{geometryReasons[reason] ?? reason}</li>)}</ul>
            <p>منبع، ویرایش و تاریخ اعتبار را در بخش «عقب‌نشینی و اصلاحی» ثبت کنید.</p>
          </details> : null}
          {report.envelope?.max_footprint_m2 != null ? <p>حد مساحت ساخت با سطح اشغال معتبر: {geometryNumber(report.envelope.max_footprint_m2)} متر مربع.</p> : <p className="field-hint">حد سطح اشغال بدون منبع معتبر محاسبه نمی‌شود.</p>}
          {report.source_versions ? <p className="field-hint">نسخهٔ ورودی‌ها: زمین {report.source_versions.parcel}، دسترسی {report.source_versions.access}، عقب‌نشینی {report.source_versions.setbacks}، سطح اشغال {report.source_versions.coverage}.</p> : null}
        </> : null}
        <p className="field-hint">محاسبهٔ اولیه بر اساس دادهٔ واردشده؛ نه تأیید قانونی یا مجوز ساخت. شکل هاشورخورده پاکت عقب‌نشینی است، نه پلان پیشنهادی. دقت قوس‌های آن حداکثر ۱ میلی‌متر محافظه‌کارانه است.</p>
      </div>
    </section>
  );
}
