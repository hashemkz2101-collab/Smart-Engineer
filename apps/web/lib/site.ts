// Layout of the site / land data sections (SITE-001, SITE-002). The API is the
// source of truth for validation and for every computed value; this file only
// describes labels and input types.

export type SiteField = {
  name: string;
  label: string;
  kind: "text" | "textarea" | "choice" | "number" | "boolean";
  choices?: { value: string; label: string }[];
  ltr?: boolean;
  required?: boolean;
  hint?: string;
};

export type SiteList = {
  name: string;
  label: string;
  hint?: string;
  columns: SiteField[];
  // Always sent, even when empty: an empty list means "none exist".
  always?: boolean;
};

export type SiteSectionDef = {
  key: string;
  title: string;
  intro?: string;
  fields: SiteField[];
  lists: SiteList[];
};

const sides = [
  { value: "north", label: "شمال" },
  { value: "south", label: "جنوب" },
  { value: "east", label: "شرق" },
  { value: "west", label: "غرب" },
];

const described: SiteField[] = [
  { name: "description", label: "توضیح", kind: "text", required: true },
  { name: "notes", label: "یادداشت", kind: "text" },
];

export const siteSections: SiteSectionDef[] = [
  {
    key: "parcel",
    title: "قطعه و مساحت",
    intro:
      "ابعاد را به متر وارد کنید. مساحت از روی ابعاد محاسبه می‌شود و اختلاف آن با مساحت اظهارشده گزارش می‌شود؛ این گزارش جای نقشه‌برداری رسمی را نمی‌گیرد.",
    fields: [
      {
        name: "shape",
        label: "شکل قطعه",
        kind: "choice",
        required: true,
        choices: [
          { value: "rectangular", label: "مستطیل" },
          { value: "polygon", label: "چندضلعی" },
          { value: "irregular", label: "نامنظم" },
        ],
      },
      { name: "width_m", label: "عرض (متر)", kind: "number", ltr: true, hint: "برای شکل مستطیل." },
      { name: "depth_m", label: "طول (متر)", kind: "number", ltr: true, hint: "برای شکل مستطیل." },
      { name: "declared_area_m2", label: "مساحت اظهارشده (متر مربع)", kind: "number", ltr: true },
      { name: "survey_reference", label: "مرجع نقشه‌برداری", kind: "text" },
      { name: "coordinate_system", label: "سیستم مختصات", kind: "text", ltr: true },
    ],
    lists: [
      {
        name: "vertices",
        label: "رئوس مرز (به ترتیب دور قطعه)",
        hint: "برای چندضلعی و نامنظم؛ دست‌کم سه نقطه، مختصات محلی به متر.",
        columns: [
          { name: "x", label: "X", kind: "number", ltr: true, required: true },
          { name: "y", label: "Y", kind: "number", ltr: true, required: true },
        ],
      },
      {
        name: "sides",
        label: "طول اضلاع",
        columns: [
          { name: "label", label: "ضلع", kind: "text" },
          { name: "length_m", label: "طول (متر)", kind: "number", ltr: true, required: true },
        ],
      },
      {
        name: "survey_points",
        label: "نقاط نقشه‌برداری",
        columns: [
          { name: "label", label: "نام نقطه", kind: "text", ltr: true },
          { name: "x", label: "X", kind: "number", ltr: true, required: true },
          { name: "y", label: "Y", kind: "number", ltr: true, required: true },
        ],
      },
    ],
  },
  {
    key: "access",
    title: "دسترسی و جهت",
    fields: [
      {
        name: "north_angle_deg",
        label: "زاویهٔ شمال جغرافیایی (درجه)",
        kind: "number",
        ltr: true,
        hint: "بین ۰ تا ۳۶۰ نسبت به بالای نقشه.",
      },
      {
        name: "street_direction",
        label: "جهت خیابان",
        kind: "choice",
        required: true,
        choices: [
          ...sides,
          { value: "northeast", label: "شمال‌شرقی" },
          { value: "northwest", label: "شمال‌غربی" },
          { value: "southeast", label: "جنوب‌شرقی" },
          { value: "southwest", label: "جنوب‌غربی" },
        ],
      },
      { name: "frontage_length_m", label: "طول بر (متر)", kind: "number", ltr: true },
      { name: "road_width_m", label: "عرض معبر (متر)", kind: "number", ltr: true, required: true },
      { name: "access_fronts", label: "تعداد بر دسترسی", kind: "number", ltr: true, required: true },
    ],
    lists: [],
  },
  {
    key: "terrain",
    title: "توپوگرافی",
    fields: [
      {
        name: "topography",
        label: "وضعیت زمین",
        kind: "choice",
        required: true,
        choices: [
          { value: "flat", label: "مسطح" },
          { value: "gentle_slope", label: "شیب ملایم" },
          { value: "steep_slope", label: "شیب تند" },
          { value: "terraced", label: "پلکانی" },
          { value: "irregular", label: "ناهموار" },
        ],
      },
      { name: "slope_percent", label: "شیب (درصد)", kind: "number", ltr: true },
      { name: "level_difference_m", label: "اختلاف تراز (متر)", kind: "number", ltr: true },
      { name: "elevation_m", label: "ارتفاع از سطح دریا (متر)", kind: "number", ltr: true },
    ],
    lists: [],
  },
  {
    key: "surroundings",
    title: "محیط اطراف",
    intro: "هر فهرست را جداگانه پر کنید؛ فهرست خالی یعنی «وجود ندارد».",
    fields: [],
    lists: [
      {
        name: "neighbors",
        label: "همسایگان",
        always: true,
        columns: [
          { name: "side", label: "سمت", kind: "choice", choices: sides, required: true },
          {
            name: "kind",
            label: "نوع",
            kind: "choice",
            choices: [
              { value: "building", label: "ساختمان" },
              { value: "vacant_land", label: "زمین خالی" },
              { value: "road", label: "معبر" },
              { value: "other", label: "سایر" },
            ],
          },
          { name: "shared_wall", label: "دیوار مشترک", kind: "boolean" },
          {
            name: "barrier",
            label: "حائل",
            kind: "choice",
            choices: [
              { value: "none", label: "ندارد" },
              { value: "wall", label: "دیوار" },
              { value: "fence", label: "نرده" },
              { value: "other", label: "سایر" },
            ],
          },
          { name: "notes", label: "یادداشت", kind: "text" },
        ],
      },
      { name: "trees", label: "درختان", always: true, columns: described },
      { name: "wells", label: "چاه‌ها", always: true, columns: described },
      { name: "channels", label: "کانال‌ها و جوی‌ها", always: true, columns: described },
      {
        name: "existing_utilities",
        label: "تأسیسات موجود",
        always: true,
        columns: [
          ...described,
          {
            name: "utility",
            label: "نوع",
            kind: "choice",
            choices: [
              { value: "water", label: "آب" },
              { value: "electricity", label: "برق" },
              { value: "gas", label: "گاز" },
              { value: "sewage", label: "فاضلاب" },
              { value: "telecom", label: "مخابرات" },
              { value: "other", label: "سایر" },
            ],
          },
        ],
      },
      { name: "easements", label: "حریم‌ها و ارتفاق", always: true, columns: described },
    ],
  },
  {
    key: "soil",
    title: "خاک",
    intro:
      "همهٔ فیلدها اختیاری‌اند. مقداری که وارد نکنید «ثبت‌نشده» می‌ماند و هیچ مقدار پیش‌فرضی جایگزین آن نمی‌شود.",
    fields: [
      {
        name: "soil_type",
        label: "نوع خاک",
        kind: "choice",
        choices: [
          { value: "rock", label: "سنگ" },
          { value: "gravel", label: "شن" },
          { value: "sand", label: "ماسه" },
          { value: "silt", label: "سیلت" },
          { value: "clay", label: "رس" },
          { value: "mixed", label: "مخلوط" },
          { value: "other", label: "سایر" },
        ],
      },
      { name: "bearing_capacity_kpa", label: "ظرفیت باربری (کیلوپاسکال)", kind: "number", ltr: true },
      { name: "groundwater_depth_m", label: "عمق آب زیرزمینی (متر)", kind: "number", ltr: true },
      { name: "report_reference", label: "مرجع گزارش ژئوتکنیک", kind: "text" },
    ],
    lists: [],
  },
];

export function fieldLabel(def: SiteSectionDef, name: string): string {
  return (
    def.fields.find((field) => field.name === name)?.label ??
    def.lists.find((list) => list.name === name)?.label ??
    name
  );
}
