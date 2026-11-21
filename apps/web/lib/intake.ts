// Field layout of the project intake steps. The API is the source of truth for
// validation; this file only describes labels and input types.

export type FieldDef = {
  name: string;
  label: string;
  kind: "text" | "textarea" | "choice" | "number";
  choices?: { value: string; label: string }[];
  ltr?: boolean;
  required?: boolean;
  hint?: string;
};

export type StepDef = { key: string; title: string; fields: FieldDef[] };

export const intakeSteps: StepDef[] = [
  {
    key: "identity",
    title: "مشخصات کلی",
    fields: [
      { name: "project_code", label: "کد پروژه", kind: "text", ltr: true },
      {
        name: "purpose",
        label: "هدف پروژه",
        kind: "choice",
        required: true,
        choices: [
          { value: "residence", label: "سکونت" },
          { value: "investment", label: "سرمایه‌گذاری" },
          { value: "sale", label: "فروش" },
          { value: "rent", label: "اجاره" },
          { value: "mixed_use", label: "استفادهٔ ترکیبی" },
        ],
      },
    ],
  },
  {
    key: "location",
    title: "موقعیت",
    fields: [
      { name: "province", label: "استان", kind: "text", required: true },
      { name: "city", label: "شهر", kind: "text", required: true },
      { name: "address", label: "نشانی", kind: "textarea" },
      {
        name: "latitude",
        label: "عرض جغرافیایی",
        kind: "number",
        ltr: true,
        hint: "عددی بین ۹۰- تا ۹۰؛ همراه با طول جغرافیایی.",
      },
      {
        name: "longitude",
        label: "طول جغرافیایی",
        kind: "number",
        ltr: true,
        hint: "عددی بین ۱۸۰- تا ۱۸۰.",
      },
    ],
  },
  {
    key: "people",
    title: "افراد",
    fields: [
      { name: "client", label: "کارفرما", kind: "text", required: true },
      { name: "owner", label: "مالک", kind: "text" },
      { name: "responsible_engineer", label: "مهندس مسئول", kind: "text" },
      { name: "team_notes", label: "اعضای تیم و توضیحات", kind: "textarea" },
    ],
  },
  {
    key: "legal",
    title: "وضعیت زمین",
    fields: [
      {
        name: "ownership_status",
        label: "وضعیت مالکیت",
        kind: "choice",
        choices: [
          { value: "unknown", label: "نامشخص" },
          { value: "owned", label: "ملکی" },
          { value: "leased", label: "اجاره‌ای" },
          { value: "partnership", label: "مشارکتی" },
          { value: "other", label: "سایر" },
        ],
      },
      {
        name: "deed_status",
        label: "وضعیت سند",
        kind: "choice",
        choices: [
          { value: "unknown", label: "نامشخص" },
          { value: "has_deed", label: "سند دارد" },
          { value: "no_deed", label: "سند ندارد" },
          { value: "in_process", label: "در حال انجام" },
        ],
      },
      { name: "restrictions", label: "محدودیت‌های حقوقی", kind: "textarea" },
      { name: "notes", label: "توضیحات", kind: "textarea" },
    ],
  },
];
