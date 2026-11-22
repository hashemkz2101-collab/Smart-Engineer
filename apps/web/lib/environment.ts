// Environmental and technical-condition inputs (ENV-001). The API is the source of
// truth for validation and the derived status; this file only has labels and types.

import type { SiteField } from "./site";
import type { ZoningDef } from "./zoning";

const num = (name: string, label: string): SiteField => ({ name, label, kind: "number", ltr: true });
const notes = (name: string, label: string): SiteField => ({ name, label, kind: "textarea" });
const risk = (name: string, label: string): SiteField => ({
  name,
  label,
  kind: "choice",
  choices: [
    { value: "none", label: "ندارد" },
    { value: "low", label: "کم" },
    { value: "medium", label: "متوسط" },
    { value: "high", label: "زیاد" },
  ],
});
const utility = (): SiteField[] => [
  {
    name: "availability",
    label: "وضعیت دسترسی",
    kind: "choice",
    choices: [
      { value: "available", label: "موجود است" },
      { value: "not_available", label: "موجود نیست" },
      { value: "planned", label: "در برنامه است" },
    ],
  },
  num("connection_distance_m", "فاصلهٔ تا نقطهٔ اتصال (متر)"),
  notes("notes", "توضیحات"),
];

export const environmentFields: ZoningDef[] = [
  {
    key: "climate",
    title: "اقلیم",
    fields: [
      { name: "climate_zone", label: "پهنهٔ اقلیمی", kind: "text" },
      num("mean_annual_temperature_c", "میانگین دمای سالانه (درجهٔ سانتی‌گراد)"),
      notes("climate_notes", "توضیحات اقلیم"),
    ],
  },
  {
    key: "solar",
    title: "تابش خورشید",
    fields: [
      num("solar_radiation_kwh_m2_day", "تابش روزانه (کیلووات‌ساعت بر متر مربع)"),
      num("sunshine_hours_per_year", "ساعات آفتابی سالانه"),
      notes("solar_notes", "توضیحات تابش"),
    ],
  },
  {
    key: "wind",
    title: "باد غالب",
    fields: [
      {
        name: "prevailing_direction",
        label: "جهت باد غالب",
        kind: "choice",
        choices: [
          { value: "north", label: "شمال" },
          { value: "northeast", label: "شمال‌شرقی" },
          { value: "east", label: "شرق" },
          { value: "southeast", label: "جنوب‌شرقی" },
          { value: "south", label: "جنوب" },
          { value: "southwest", label: "جنوب‌غربی" },
          { value: "west", label: "غرب" },
          { value: "northwest", label: "شمال‌غربی" },
        ],
      },
      num("mean_speed_ms", "میانگین سرعت باد (متر بر ثانیه)"),
      notes("wind_notes", "توضیحات باد"),
    ],
  },
  {
    key: "rainfall",
    title: "بارندگی",
    fields: [
      num("annual_mm", "بارش سالانه (میلی‌متر)"),
      num("max_daily_mm", "حداکثر بارش روزانه (میلی‌متر)"),
      notes("rainfall_notes", "توضیحات بارندگی"),
    ],
  },
  {
    key: "design_temperature",
    title: "دمای طراحی و آسایش",
    fields: [
      num("summer_design_c", "دمای طراحی تابستان (درجهٔ سانتی‌گراد)"),
      num("winter_design_c", "دمای طراحی زمستان (درجهٔ سانتی‌گراد)"),
      notes("comfort_notes", "شرایط آسایش"),
    ],
  },
  {
    key: "hazards",
    title: "خطرهای طبیعی",
    fields: [
      risk("flood_risk", "خطر سیل"),
      risk("landslide_risk", "خطر زمین‌لغزش"),
      risk("subsidence_risk", "خطر نشست زمین"),
      notes("other_hazards", "سایر خطرها"),
    ],
  },
  {
    key: "seismicity",
    title: "لرزه‌خیزی",
    fields: [
      { name: "seismic_zone", label: "پهنهٔ لرزه‌خیزی", kind: "text" },
      num("design_pga_g", "شتاب مبنای طرح (برحسب g)"),
      num("nearest_fault_km", "فاصله تا نزدیک‌ترین گسل (کیلومتر)"),
      notes("seismic_notes", "توضیحات لرزه‌خیزی"),
    ],
  },
  { key: "water", title: "آب", fields: utility() },
  { key: "electricity", title: "برق", fields: utility() },
  { key: "gas", title: "گاز", fields: utility() },
  { key: "sewer", title: "فاضلاب", fields: utility() },
  { key: "telecom", title: "مخابرات", fields: utility() },
  {
    key: "energy",
    title: "انرژی و بهره‌وری",
    fields: [
      notes("energy_constraints", "محدودیت‌های انرژی"),
      notes("efficiency_requirements", "الزامات بهره‌وری"),
    ],
  },
];

export const environmentSourceFields: SiteField[] = [
  {
    name: "source_type",
    label: "نوع مرجع داده",
    kind: "choice",
    choices: [
      { value: "meteorological_station", label: "ایستگاه هواشناسی" },
      { value: "national_standard", label: "استاندارد ملی" },
      { value: "official_map", label: "نقشهٔ رسمی" },
      { value: "utility_company", label: "شرکت خدمات‌رسان" },
      { value: "municipality", label: "شهرداری" },
      { value: "site_survey", label: "برداشت میدانی" },
      { value: "report", label: "گزارش" },
      { value: "other", label: "سایر" },
    ],
  },
  { name: "source_title", label: "عنوان مرجع داده", kind: "text" },
  { name: "source_reference", label: "شماره یا پیوند سند", kind: "text", ltr: true },
  {
    name: "location_reference",
    label: "محلی که داده به آن مربوط است",
    kind: "text",
    hint: "مثلاً نام ایستگاه، شهر یا آدرس زمین.",
  },
  {
    name: "source_date",
    label: "تاریخ داده",
    kind: "text",
    ltr: true,
    hint: "به شکل سال-ماه-روز، مثل 1403-12-01؛ تقویم را هم انتخاب کنید.",
  },
  {
    name: "source_calendar",
    label: "تقویم این تاریخ",
    kind: "choice",
    choices: [
      { value: "jalali", label: "شمسی" },
      { value: "gregorian", label: "میلادی" },
    ],
  },
  {
    name: "source_verified",
    label: "مرجع بالا این مقدارها را تأیید شده می‌دانم",
    kind: "boolean",
  },
];

export const environmentMissingLabels: Record<string, string> = {
  source_type: "نوع مرجع",
  source_title_or_reference: "عنوان یا شمارهٔ سند",
  location_reference: "محل داده",
  source_date: "تاریخ داده",
};
