// Types and Persian labels for conceptual layout alternatives (ARCH-002). The API is the
// source of truth for every placement, number and reason; this file only names them.

export type Placement = {
  space_id: string;
  kind: string;
  x: number;
  y: number;
  width: number;
  height: number;
  area_m2: number;
  area_basis: "target" | "range_midpoint";
};

export type Alternative = {
  id: string;
  strategy: string;
  criteria: string[];
  assumptions: string[];
  not_evaluated: string[];
  limitations: string[];
  floors: { floor: number; placements: Placement[]; used_area_m2: number }[];
  unplaced: { space_id: string; kind: string; reason: string }[];
  metrics: {
    placed_spaces: number;
    unplaced_spaces: number;
    placed_area_m2: number;
    fully_placed: boolean;
    floors_used: number;
    footprint_coverage_percent?: number;
  };
};

export type LayoutData = {
  status: "alternatives" | "infeasible";
  reasons: string[];
  details: Record<string, unknown>;
  alternatives: Alternative[];
  envelope_polygons?: { exterior: [number, number][]; holes: [number, number][][] }[];
};

export type LayoutState = {
  exists: boolean;
  data: LayoutData | null;
  version: number;
  stale: boolean;
  updated_at: string | null;
};

export const strategyLabels: Record<string, string> = {
  privacy_bands: "پهنه‌بندی خصوصی‌بودن (عمومی نزدیک ورودی، خصوصی دورتر)",
  largest_first_compact: "فضاهای بزرگ‌تر اول، فشرده از گوشهٔ پایین‌چپ",
  largest_first_mirrored: "فضاهای بزرگ‌تر اول، فشرده از گوشهٔ بالاراست",
};

export const criteriaLabels: Record<string, string> = {
  public_rooms_nearest_the_front: "فضاهای عمومی نزدیک‌ترین به ضلع جلو",
  private_rooms_farthest_from_the_front: "اتاق‌های خصوصی دورترین از ضلع جلو",
  largest_spaces_first: "فضاهای بزرگ‌تر اول جانمایی می‌شوند",
  compact_from_the_lower_left_corner: "چیدمان فشرده از گوشهٔ پایین‌چپ",
  compact_from_the_upper_right_corner: "چیدمان فشرده از گوشهٔ بالاراست",
};

export const assumptionLabels: Record<string, string> = {
  front_edge_not_identified_lowest_y_used:
    "ضلع جلو در زمین مشخص نشده؛ پایین‌ترین Y به‌عنوان جهت مرجع استفاده شد.",
};

export const notEvaluatedLabels: Record<string, string> = {
  orientation_and_daylight: "جهت‌گیری و نور روز",
  views_and_privacy_between_buildings: "دید و خصوصی‌بودن نسبت به ساختمان‌های مجاور",
  adjacency_and_circulation: "مجاورت فضاها و گردش",
  structure_and_stacking: "سازه و هم‌راستایی طبقات",
  stairs_elevators_and_egress: "پله، آسانسور و خروج اضطراری",
  regulation_compliance: "انطباق با ضوابط",
};

export const layoutLimitationLabels: Record<string, string> = {
  conceptual_blocks_not_a_plan: "بلوک‌های مفهومی‌اند، نه پلان؛ دیوار، در و پنجره ندارند.",
  net_room_areas_only: "فقط مساحت خالص فضاها؛ دیوار و راهرو شامل نیست.",
  same_envelope_on_every_floor: "در همهٔ طبقات همان محدودهٔ قابل ساخت فرض شده است.",
  not_an_approved_design: "طرح تأییدشده یا مجوز ساخت نیست.",
};

export const unplacedLabels: Record<string, string> = {
  outdoor_space_not_modelled: "فضای باز؛ در این مرحله مدل نمی‌شود",
  parking_not_modelled: "پارکینگ؛ در این مرحله مدل نمی‌شود",
  area_not_given: "مساحت وارد نشده",
  area_range_incomplete: "فقط یکی از حداقل/حداکثر مساحت وارد شده",
  did_not_fit: "در محدودهٔ قابل ساخت جا نشد",
};

export const infeasibleLabels: Record<string, string> = {
  parcel_invalid_or_missing: "مرز زمین ثبت نشده یا معتبر نیست.",
  space_schedule_missing: "فهرست فضاها هنوز ساخته نشده است.",
  space_schedule_stale: "فهرست فضاها با برنامهٔ فعلی هم‌خوان نیست؛ آن را دوباره بسازید.",
  envelope_not_computed: "محدودهٔ قابل ساخت محاسبه نشد؛ منبع ضوابط ناقص یا نامعتبر است.",
  envelope_empty: "پس از اعمال عقب‌نشینی‌ها محدودهٔ قابل ساختی باقی نمی‌ماند.",
  no_spaces_in_schedule: "فهرست فضاها خالی است.",
  no_placeable_spaces: "هیچ فضایی با مساحت قابل جانمایی در داخل ساختمان نیست.",
  required_area_exceeds_capacity: "مجموع مساحت فضاها از ظرفیت محدودهٔ قابل ساخت در طبقات بیشتر است.",
  too_many_spaces_for_conceptual_layout: "تعداد فضاها برای چیدمان مفهومی بیش از حد مجاز است.",
  fewer_than_two_distinct_alternatives: "کمتر از دو گزینهٔ متمایز به‌دست آمد.",
  front_m_required: "عقب‌نشینی جلو ثبت نشده است.",
  rear_m_required: "عقب‌نشینی عقب ثبت نشده است.",
  left_m_required: "عقب‌نشینی چپ ثبت نشده است.",
  right_m_required: "عقب‌نشینی راست ثبت نشده است.",
  edge_mapping_required: "نقش اضلاع زمین (جلو، عقب، چپ، راست) مشخص نشده است.",
  invalid_edge_mapping: "نقش‌دهی اضلاع زمین معتبر نیست.",
  source_not_verified: "منبع ضوابط تأیید نشده است.",
  source_expired: "اعتبار منبع ضوابط تمام شده است.",
  source_not_yet_valid: "منبع ضوابط هنوز معتبر نشده است.",
  correction_needs_human_review: "اصلاحات متنی ضوابط نیاز به بررسی انسانی دارد.",
};
