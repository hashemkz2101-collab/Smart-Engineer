// Persian labels and error messages. Error codes come from the API envelope
// ({"error": {"code": ...}}); unknown codes fall back to a generic message.

const errorMessages: Record<string, string> = {
  invalid_credentials: "ایمیل یا رمز عبور درست نیست.",
  account_locked: "تلاش‌های ناموفق زیاد بود. چند دقیقه بعد دوباره امتحان کنید.",
  email_taken: "حسابی با این ایمیل وجود دارد.",
  weak_password:
    "رمز عبور باید دست‌کم ۱۰ نویسه باشد و ساده یا شبیه بخش اول ایمیل نباشد.",
  invalid_email: "نشانی ایمیل درست نیست.",
  invalid_display_name: "نام لازم است و باید حداکثر ۲۰۰ نویسه باشد.",
  invalid_token: "پیوند یا کد نامعتبر است یا منقضی شده است.",
  email_not_verified: "ایمیل شما هنوز تأیید نشده است.",
  forbidden: "اجازهٔ انجام این کار را ندارید.",
  http_401: "لطفاً دوباره وارد شوید.",
  http_403: "اجازهٔ انجام این کار را ندارید.",
  http_404: "مورد درخواستی پیدا نشد.",
  http_503: "سرویس در حال حاضر در دسترس نیست.",
  validation_error: "اطلاعات واردشده درست نیست.",
  internal_error: "خطای داخلی رخ داد. دوباره تلاش کنید.",
  network_error: "ارتباط با سرور برقرار نشد.",
  invalid_name: "نام لازم است و باید حداکثر ۲۰۰ نویسه باشد.",
  invalid_project_type: "نوع پروژه درست نیست.",
  invalid_role: "نقش انتخاب‌شده درست نیست.",
  user_not_in_organization: "این کاربر عضو سازمان نیست.",
  already_member: "این کاربر از قبل عضو است.",
  last_owner: "هر پروژه باید دست‌کم یک مالک داشته باشد.",
  not_archived: "این پروژه بایگانی نشده است.",
  not_found: "مورد درخواستی پیدا نشد.",
  cannot_remove_owner: "مالک سازمان را نمی‌توان حذف کرد.",
  owner_role_fixed: "نقش مالک سازمان قابل تغییر نیست.",
  invalid_site: "برخی فیلدهای داده‌های زمین درست نیستند؛ موارد مشخص‌شده را اصلاح کنید.",
  invalid_requirements: "برخی فیلدهای نیازمندی‌ها درست نیستند؛ موارد مشخص‌شده را اصلاح کنید.",
  invalid_environment: "برخی فیلدهای شرایط محیطی درست نیستند؛ موارد مشخص‌شده را اصلاح کنید.",
  invalid_zoning: "برخی فیلدهای ضوابط درست نیستند؛ موارد مشخص‌شده را اصلاح کنید.",
  invalid_intake: "برخی فیلدها درست نیستند؛ موارد مشخص‌شده را اصلاح کنید.",
  version_conflict:
    "این مرحله در جای دیگری تغییر کرده است. اطلاعات را دوباره بارگذاری کنید.",
  file_too_large: "حجم فایل از حد مجاز (۱۰ مگابایت) بیشتر است.",
  unsupported_type: "این نوع فایل مجاز نیست. فقط PDF، PNG، JPEG و WebP پذیرفته می‌شود.",
  extension_mismatch: "پسوند فایل با محتوای آن یکی نیست.",
  empty_file: "فایل خالی است.",
  invalid_kind: "نوع سند را انتخاب کنید.",
  invalid_date: "تاریخ سند معتبر نیست؛ به شکل میلادی سال-ماه-روز وارد کنید.",
  invalid_name: "نام فایل معتبر نیست.",
  invalid_ownership: "متن مالکیت بیش از حد طولانی است.",
  too_many_files: "تعداد فایل‌های این پروژه به سقف مجاز رسیده است.",
  not_available: "این فایل برای دانلود در دسترس نیست.",
  unknown_step: "این مرحله وجود ندارد.",
};

export function messageForCode(code: string): string {
  return errorMessages[code] ?? "خطایی رخ داد. دوباره تلاش کنید.";
}

export const projectTypeLabels: Record<string, string> = {
  residential_house: "خانهٔ مسکونی (ویلایی)",
  residential_apartment: "آپارتمان مسکونی",
  commercial: "تجاری",
  mixed_use: "مختلط",
  other: "سایر",
};

export const projectRoleLabels: Record<string, string> = {
  owner: "مالک / کارفرما",
  architect: "معمار",
  structural_engineer: "مهندس سازه",
  mep_engineer: "مهندس تأسیسات",
  quantity_surveyor: "متره‌گر / برآوردکننده",
  org_admin: "مدیر سازمان",
};

export const orgRoleLabels: Record<string, string> = {
  owner: "مالک",
  admin: "مدیر",
  member: "عضو",
};

export const activityLabels: Record<string, string> = {
  "project.created": "پروژه ایجاد شد",
  "project.updated": "مشخصات پروژه ویرایش شد",
  "project.archived": "پروژه بایگانی شد",
  "project.restored": "پروژه از بایگانی بازگردانده شد",
  "project.member_added": "عضوی به پروژه اضافه شد",
  "project.member_role_changed": "نقش یک عضو تغییر کرد",
  "project.member_removed": "عضوی از پروژه حذف شد",
  "project.requirements_saved": "نیازمندی‌های کارفرما ذخیره شد",
  "project.environment_saved": "شرایط محیطی ذخیره شد",
  "project.zoning_saved": "ضوابط شهرسازی ذخیره شد",
  "project.file_uploaded": "فایل بارگذاری شد",
  "project.file_deleted": "فایل حذف شد",
  "project.site_saved": "داده‌های زمین ذخیره شد",
  "project.intake_saved": "اطلاعات ورودی پروژه ذخیره شد",
};

export function formatDate(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString("fa-IR");
}

export const fieldReasonMessages: Record<string, string> = {
  not_text: "مقدار باید متن باشد.",
  too_long: "متن از حد مجاز طولانی‌تر است.",
  not_a_number: "یک عدد معتبر وارد کنید.",
  out_of_range: "عدد خارج از محدودهٔ مجاز است.",
  invalid_choice: "یکی از گزینه‌های موجود را انتخاب کنید.",
  unknown_field: "این فیلد شناخته‌شده نیست.",
  coordinates_need_both: "عرض و طول جغرافیایی باید با هم وارد شوند.",
  winter_above_summer: "دمای طراحی زمستان نباید از دمای تابستان بیشتر باشد.",
  range_inverted: "حداقل نباید از حداکثر بیشتر باشد.",
  currency_required: "با مبلغ، واحد آن را هم انتخاب کنید.",
  invalid_url: "پیوند باید با http:// یا https:// شروع شود.",
  invalid_date: "تاریخ معتبر نیست؛ به شکل سال-ماه-روز وارد کنید.",
  calendar_required: "با تاریخ، تقویم آن را هم انتخاب کنید.",
  not_an_integer: "یک عدد صحیح وارد کنید.",
  not_a_boolean: "مقدار باید بله یا خیر باشد.",
  not_a_list: "فهرست درست نیست.",
  not_an_object: "ردیف درست نیست.",
  too_many_items: "تعداد ردیف‌ها از حد مجاز بیشتر است.",
  required: "این مورد ضروری است.",
  too_few_points: "دست‌کم سه نقطه لازم است.",
  degenerate: "نقاط مساحت صفر می‌سازند.",
  self_intersecting: "مرز قطعه خودش را قطع می‌کند.",
};
