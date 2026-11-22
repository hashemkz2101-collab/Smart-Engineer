// Zoning / building-control inputs (RULE-DATA-001). The API is the source of truth
// for validation and for the derived status; this file only has labels and types.

import type { SiteField } from "./site";

export type ZoningDef = { key: string; title: string; fields: SiteField[] };

const notes = (name: string, label: string): SiteField => ({ name, label, kind: "textarea" });
const num = (name: string, label: string): SiteField => ({ name, label, kind: "number", ltr: true });

export const zoningFields: ZoningDef[] = [
  {
    key: "land_use",
    title: "کاربری و منطقه",
    fields: [
      { name: "zone_name", label: "نام منطقه یا پهنه", kind: "text" },
      { name: "land_use", label: "کاربری مجاز", kind: "text" },
    ],
  },
  {
    key: "coverage",
    title: "سطح اشغال",
    fields: [num("max_coverage_percent", "حداکثر سطح اشغال (درصد)")],
  },
  {
    key: "density",
    title: "تراکم و زیربنا",
    fields: [
      num("max_density_percent", "تراکم مجاز (درصد)"),
      num("max_floor_area_m2", "حداکثر زیربنای مجاز (متر مربع)"),
    ],
  },
  {
    key: "floors_height",
    title: "تعداد طبقات و ارتفاع",
    fields: [num("max_floors", "حداکثر تعداد طبقات"), num("max_height_m", "حداکثر ارتفاع (متر)")],
  },
  {
    key: "setbacks",
    title: "عقب‌نشینی و اصلاحی",
    fields: [
      num("front_m", "عقب‌نشینی از جلو (متر)"),
      num("rear_m", "عقب‌نشینی از عقب (متر)"),
      num("left_m", "عقب‌نشینی از چپ (متر)"),
      num("right_m", "عقب‌نشینی از راست (متر)"),
      notes("correction_notes", "اصلاحی و توضیحات"),
    ],
  },
  {
    key: "parking_access",
    title: "پارکینگ و دسترسی",
    fields: [
      num("min_parking_spaces", "حداقل تعداد پارکینگ"),
      notes("parking_notes", "ضوابط پارکینگ"),
      notes("access_notes", "ضوابط دسترسی"),
    ],
  },
  {
    key: "daylight_openings",
    title: "نورگیری و بازشو",
    fields: [
      notes("daylight_notes", "ضوابط نورگیری"),
      notes("courtyard_notes", "ضوابط حیاط و پاسیو"),
      notes("opening_notes", "ضوابط بازشوها"),
    ],
  },
  {
    key: "circulation",
    title: "پله، آسانسور و خروج",
    fields: [
      {
        name: "elevator",
        label: "آسانسور",
        kind: "choice",
        choices: [
          { value: "required", label: "الزامی" },
          { value: "not_required", label: "الزامی نیست" },
        ],
      },
      notes("stair_notes", "ضوابط پله"),
      notes("ramp_notes", "ضوابط رمپ"),
      notes("exit_notes", "ضوابط خروج"),
    ],
  },
  {
    key: "local_constraints",
    title: "محدودیت‌های محلی",
    fields: [notes("constraints", "محدودیت‌ها و ضوابط خاص شهرداری")],
  },
];

export const sourceFields: SiteField[] = [
  {
    name: "source_type",
    label: "نوع منبع",
    kind: "choice",
    choices: [
      { value: "municipality_letter", label: "نامهٔ شهرداری" },
      { value: "master_plan", label: "طرح جامع" },
      { value: "detailed_plan", label: "طرح تفصیلی" },
      { value: "permit_office_inquiry", label: "استعلام دفتر پروانه" },
      { value: "regulation_document", label: "سند ضوابط" },
      { value: "other", label: "سایر" },
    ],
  },
  { name: "source_title", label: "عنوان منبع", kind: "text" },
  { name: "source_reference", label: "شماره یا پیوند سند", kind: "text", ltr: true },
  {
    name: "source_date",
    label: "تاریخ منبع",
    kind: "text",
    ltr: true,
    hint: "به شکل سال-ماه-روز، مثل 1405-02-10؛ تقویم را هم انتخاب کنید.",
  },
  {
    name: "source_calendar",
    label: "تقویم تاریخ",
    kind: "choice",
    choices: [
      { value: "jalali", label: "شمسی" },
      { value: "gregorian", label: "میلادی" },
    ],
  },
  {
    name: "source_verified",
    label: "تأیید می‌کنم این منبع مقدار بالا را تأیید می‌کند",
    kind: "boolean",
  },
];

export const statusLabels: Record<string, string> = {
  unknown: "نامشخص",
  needs_inquiry: "نیازمند استعلام",
  verified: "تأییدشده",
};

export const sourceMissingLabels: Record<string, string> = {
  source_type: "نوع منبع",
  source_date: "تاریخ منبع",
  source_title_or_reference: "عنوان یا شمارهٔ سند",
};
