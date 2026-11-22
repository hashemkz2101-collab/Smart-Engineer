// Client requirement sections (REQ-001, REQ-002, REQ-003). The API is the source of
// truth for validation; this file only describes labels and input types.

import type { SiteField, SiteSectionDef } from "./site";

const num = (name: string, label: string, required = false): SiteField => ({
  name,
  label,
  kind: "number",
  ltr: true,
  required,
});
const text = (name: string, label: string, kind: SiteField["kind"] = "text"): SiteField => ({
  name,
  label,
  kind,
});
const choice = (
  name: string,
  label: string,
  choices: [string, string][],
  required = false,
): SiteField => ({
  name,
  label,
  kind: "choice",
  required,
  choices: choices.map(([value, text]) => ({ value, label: text })),
});

const quality: [string, string][] = [
  ["economic", "اقتصادی"],
  ["standard", "استاندارد"],
  ["high", "بالا"],
  ["luxury", "لوکس"],
];

export const requirementSections: SiteSectionDef[] = [
  {
    key: "program",
    title: "برنامهٔ فضاها",
    intro: "تعداد واحد و طبقه، مساحت هدف یا بازه، و فهرست اتاق‌ها و فضاهای مورد نیاز.",
    fields: [
      num("units_count", "تعداد واحدها", true),
      num("floors_count", "تعداد طبقات", true),
      num("target_area_m2", "مساحت هدف (متر مربع)"),
      num("target_area_min_m2", "حداقل مساحت قابل قبول (متر مربع)"),
      num("target_area_max_m2", "حداکثر مساحت قابل قبول (متر مربع)"),
    ],
    lists: [
      {
        name: "rooms",
        label: "اتاق‌ها و فضاها",
        hint: "فهرست خالی یعنی فضایی لازم نیست.",
        always: true,
        columns: [
          choice(
            "kind",
            "نوع فضا",
            [
              ["bedroom", "اتاق خواب"],
              ["master_bedroom", "اتاق خواب اصلی"],
              ["kitchen", "آشپزخانه"],
              ["reception", "پذیرایی"],
              ["living", "نشیمن"],
              ["bathroom", "حمام و سرویس"],
              ["wc", "توالت"],
              ["storage", "انباری"],
              ["laundry", "رختشوی‌خانه"],
              ["office", "اتاق کار"],
              ["special", "فضای ویژه"],
              ["parking", "پارکینگ"],
              ["yard", "حیاط"],
              ["terrace", "تراس"],
              ["balcony", "بالکن"],
              ["roof_garden", "باغ بام"],
              ["green_space", "فضای سبز"],
              ["other", "سایر"],
            ],
            true,
          ),
          text("name", "نام"),
          num("count", "تعداد"),
          num("target_area_m2", "مساحت هدف (متر مربع)"),
          num("area_min_m2", "حداقل مساحت"),
          num("area_max_m2", "حداکثر مساحت"),
          text("notes", "یادداشت"),
        ],
      },
    ],
  },
  {
    key: "preferences",
    title: "ترجیحات و محدودیت‌ها",
    intro: "هر مورد جداگانه ثبت می‌شود؛ مورد وارد‌نشده «ثبت‌نشده» می‌ماند.",
    fields: [
      choice("accessibility", "نیاز دسترسی", [
        ["none", "ندارد"],
        ["older_occupants", "سالمندان"],
        ["disabled_occupants", "معلولان"],
        ["both", "هر دو"],
      ]),
      text("accessibility_notes", "توضیح دسترسی", "textarea"),
      choice("privacy_level", "سطح حریم خصوصی", [
        ["low", "کم"],
        ["medium", "متوسط"],
        ["high", "زیاد"],
      ]),
      choice("public_private_separation", "تفکیک عمومی و خصوصی", [
        ["not_needed", "لازم نیست"],
        ["preferred", "ترجیح می‌دهم"],
        ["required", "الزامی است"],
      ]),
      text("privacy_notes", "توضیح حریم خصوصی", "textarea"),
      text("style", "سبک معماری"),
      choice("quality_level", "سطح کیفیت", quality),
      choice("material_level", "سطح مصالح", quality),
      text("material_notes", "توضیح مصالح", "textarea"),
      num("budget_amount", "بودجهٔ هدف"),
      choice("budget_currency", "واحد بودجه", [
        ["toman", "تومان"],
        ["rial", "ریال"],
      ]),
      choice("budget_flexibility", "انعطاف بودجه", [
        ["fixed", "ثابت"],
        ["flexible", "انعطاف‌پذیر"],
      ]),
      text("future_expansion", "توسعهٔ آینده", "textarea"),
      text("change_of_use", "تغییر کاربری در آینده", "textarea"),
    ],
    lists: [
      {
        name: "priorities",
        label: "اولویت‌ها",
        columns: [
          { name: "item", label: "اولویت", kind: "text", required: true },
          num("rank", "رتبه"),
        ],
      },
      {
        name: "constraints",
        label: "الزامات و محدودیت‌ها",
        columns: [
          choice(
            "level",
            "سطح",
            [
              ["mandatory", "الزامی"],
              ["preferred", "ترجیحی"],
              ["unacceptable", "غیرقابل قبول"],
            ],
            true,
          ),
          { name: "description", label: "توضیح", kind: "text", required: true },
        ],
      },
    ],
  },
  {
    key: "references",
    title: "نمونه‌های مرجع",
    intro:
      "برای هر نمونه برچسب و توضیح بنویسید و در صورت وجود پیوند آن را بدهید. بارگذاری فایل تصویر در مرحلهٔ مدیریت فایل‌ها اضافه می‌شود.",
    fields: [],
    lists: [
      {
        name: "items",
        label: "نمونه‌ها",
        always: true,
        columns: [
          { name: "label", label: "برچسب", kind: "text", required: true },
          text("explanation", "توضیح"),
          choice("kind", "نوع", [
            ["image", "تصویر"],
            ["example_project", "پروژهٔ نمونه"],
            ["other", "سایر"],
          ]),
          { name: "url", label: "پیوند", kind: "text", ltr: true },
        ],
      },
    ],
  },
];
