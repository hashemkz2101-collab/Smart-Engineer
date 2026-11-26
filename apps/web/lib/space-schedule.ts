// Types and Persian labels for the space schedule (ARCH-001). The API is the source of
// truth for every number and flag; this file only names them.

export type ScheduleSpace = {
  id: string;
  kind: string;
  name?: string;
  room_index: number;
  ordinal: number;
  of: number;
  target_area_m2?: number;
  area_min_m2?: number;
  area_max_m2?: number;
};

export type ScheduleFlag = { code: string; severity: "info" | "warning"; room_index?: number };

export type ScheduleData = {
  source: { program_version: number; units_count?: number; floors_count?: number };
  counts_basis: string;
  spaces: ScheduleSpace[];
  totals: {
    rooms: number;
    spaces: number;
    spaces_with_area: number;
    spaces_without_area: number;
    area_lower_m2: number;
    area_upper_m2: number;
    target_sum_m2: number;
    bounds_complete: boolean;
  };
  flags: ScheduleFlag[];
  limitations: string[];
};

export type ScheduleState = {
  exists: boolean;
  data: ScheduleData | null;
  version: number;
  stale: boolean;
  program_version: number;
  program_ready: boolean;
  updated_at: string | null;
};

export const flagLabels: Record<string, string> = {
  no_rooms: "هیچ فضایی در برنامه ثبت نشده است.",
  count_not_given: "تعداد این ردیف وارد نشده؛ یک فضا در نظر گرفته شد.",
  area_not_given: "برای این ردیف هیچ مساحتی وارد نشده است.",
  target_outside_range: "مساحت هدف این ردیف خارج از بازهٔ حداقل و حداکثر خودش است.",
  program_target_outside_range: "مساحت هدف کل برنامه خارج از بازهٔ حداقل و حداکثر کل است.",
  program_exceeds_target_area:
    "حتی با کمترین مساحت‌های ثبت‌شده، مجموع فضاها از حداکثر مساحت هدف بیشتر است.",
  program_below_target_area:
    "حتی با بیشترین مساحت‌های ثبت‌شده، مجموع فضاها به حداقل مساحت هدف نمی‌رسد.",
  multi_unit_counts_not_multiplied:
    "پروژه بیش از یک واحد دارد؛ تعداد اتاق‌ها همان‌طور که نوشته شده شمرده شد و در تعداد واحد ضرب نشد.",
};

export const limitationLabels: Record<string, string> = {
  net_room_areas_only: "مجموع‌ها فقط مساحت خالص فضاهاست؛ دیوار، راهرو و سازه شامل نیست.",
  counts_as_listed_not_multiplied_by_units: "تعدادها بدون ضرب در تعداد واحد، طبق برنامه شمرده شده‌اند.",
  no_layout_or_geometry: "این فهرست چیدمان یا هندسه نیست؛ فقط فهرست و محدودهٔ مساحت فضاهاست.",
};
