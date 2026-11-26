// Display helpers only. The server validates and computes all authoritative geometry.
export type Vertex = { x: number; y: number };
export type EdgeRole = "front" | "rear" | "left" | "right";
export type EdgeAssignment = { edge_index: number; role: EdgeRole };
export type GeometryReport = {
  status: "valid" | "invalid" | "incomplete";
  engine_version: string;
  vertices?: Vertex[];
  area_m2?: number;
  perimeter_m?: number;
  area_status?: string;
  difference_m2?: number | null;
  difference_percent?: number | null;
  orientation?: string;
  north_angle_deg?: number | null;
  edges?: { index: number; length_m: number; local_bearing_deg: number; north_bearing_deg: number | null }[];
  bounds_m?: number[];
  source_versions?: Record<string, number>;
  canonical_data?: Record<string, unknown>;
  errors?: { field: string; reason: string }[];
  warnings?: string[];
  envelope?: {
    status: "computed" | "empty" | "needs_inquiry";
    reasons: string[];
    area_m2: number | null;
    max_footprint_m2: number | null;
    polygons: { exterior: [number, number][]; holes: [number, number][][]; area_m2: number }[];
  } | null;
};

export const unitFactors = { m: 1, cm: 0.01, mm: 0.001 };
export type Unit = keyof typeof unitFactors;
export const roleLabels: Record<EdgeRole, string> = {
  front: "جلو", rear: "عقب", left: "چپ", right: "راست",
};
export const geometryReasons: Record<string, string> = {
  required: "شکل و ابعاد یا رئوس زمین را کامل کنید.",
  too_few_points: "دست‌کم سه رأس وارد کنید.",
  degenerate: "این مرز مساحت معتبر ندارد.",
  self_intersecting: "اضلاع مرز یکدیگر را قطع می‌کنند.",
  duplicate_vertex: "دو رأس یکسان‌اند؛ رأس تکراری را حذف کنید.",
  zero_length_edge: "طول یک ضلع صفر یا کمتر از دقت پشتیبانی‌شده است.",
  invalid_geometry: "مرز هندسی معتبر نیست.",
  precision_insufficient: "دقت هندسه برای محاسبه کافی نیست؛ مختصات و اضلاع بسیار کوچک را بررسی کنید.",
  unsupported_unit: "واحد پشتیبانی نمی‌شود؛ متر، سانتی‌متر یا میلی‌متر را انتخاب کنید.",
  unsupported_reference: "فقط مختصات محلی صفحه‌ای پشتیبانی می‌شود؛ مختصات جغرافیایی باید با ابزار معتبر تبدیل شود.",
  not_a_number: "مختصات و ابعاد باید عدد متناهی باشند.",
  out_of_range: "مختصات یا ابعاد خارج از محدودهٔ پشتیبانی‌شده است.",
  too_many_items: "حداکثر ۲۰۰ رأس پشتیبانی می‌شود.",
  edge_mapping_required: "نوع هر ضلع را برای اعمال عقب‌نشینی مشخص کنید.",
  invalid_edge_mapping: "انتساب اضلاع معتبر نیست؛ پس از تغییر مرز آن را دوباره تعیین کنید.",
  source_type: "نوع منبع ضابطه ثبت نشده است.",
  source_date: "تاریخ منبع ضابطه ثبت نشده است.",
  source_calendar: "تقویم تاریخ منبع ثبت نشده است.",
  source_revision: "شماره یا ویرایش منبع ثبت نشده است.",
  valid_from: "آغاز اعتبار میلادی منبع ثبت نشده است.",
  valid_until: "پایان اعتبار میلادی منبع ثبت نشده است.",
  source_title_or_reference: "عنوان یا شمارهٔ سند منبع ثبت نشده است.",
  source_not_verified: "منبع ضابطه تأیید نشده است.",
  source_expired: "اعتبار منبع ضابطه تمام شده است.",
  source_not_yet_valid: "بازهٔ اعتبار منبع هنوز آغاز نشده است.",
  invalid_validity: "تاریخ اعتبار منبع معتبر نیست.",
  validity_inverted: "پایان اعتبار منبع پیش از آغاز آن است.",
  correction_needs_human_review: "اصلاحی ثبت‌شده نیازمند تفسیر متخصص است؛ پاکت خودکار صادر نمی‌شود.",
  front_m_required: "فاصلهٔ عقب‌نشینی جلو ثبت نشده است؛ صفر هم باید صریح وارد شود.",
  rear_m_required: "فاصلهٔ عقب‌نشینی عقب ثبت نشده است.",
  left_m_required: "فاصلهٔ عقب‌نشینی چپ ثبت نشده است.",
  right_m_required: "فاصلهٔ عقب‌نشینی راست ثبت نشده است.",
};

export const geometryNumber = (n: number, digits = 3) =>
  n.toLocaleString("fa-IR", { maximumFractionDigits: digits });

export function readBoundary(data: Record<string, unknown>): Vertex[] {
  if (data.shape === "rectangular") {
    const w = Number(data.width_m), h = Number(data.depth_m);
    return w > 0 && h > 0 && Number.isFinite(w) && Number.isFinite(h)
      ? [{ x: 0, y: 0 }, { x: w, y: 0 }, { x: w, y: h }, { x: 0, y: h }]
      : [];
  }
  if (!Array.isArray(data.vertices)) return [];
  return data.vertices.map((v: Record<string, unknown>) => ({ x: Number(v.x), y: Number(v.y) }));
}

export function viewBounds(points: Vertex[]): { x: number; y: number; width: number; height: number } {
  const finite = points.filter((p) => Number.isFinite(p.x) && Number.isFinite(p.y));
  if (finite.length === 0) return { x: -2, y: -2, width: 24, height: 24 };
  const xs = finite.map((p) => p.x), ys = finite.map((p) => p.y);
  const size = Math.max(Math.max(...xs) - Math.min(...xs), Math.max(...ys) - Math.min(...ys), 1);
  return { x: Math.min(...xs) - size * 0.15, y: Math.min(...ys) - size * 0.15,
    width: size * 1.3, height: size * 1.3 };
}
