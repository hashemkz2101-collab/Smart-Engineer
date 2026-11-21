import type { Metadata } from "next";

import { RegisterForm } from "../../components/register-form";

export const metadata: Metadata = { title: "ثبت‌نام | Smart Engineer" };

export default function RegisterPage() {
  return (
    <>
      <section className="page-heading" aria-labelledby="page-title">
        <h1 id="page-title">ایجاد حساب</h1>
        <p className="page-description">
          با ثبت‌نام، یک سازمان شخصی برای شما ساخته می‌شود و می‌توانید در آن پروژه
          ایجاد کنید یا دیگران را دعوت کنید.
        </p>
      </section>
      <RegisterForm />
    </>
  );
}
