import type { Metadata } from "next";

import { ForgotPasswordForm } from "../../components/forgot-password-form";

export const metadata: Metadata = { title: "بازیابی رمز عبور | Smart Engineer" };

export default function ForgotPasswordPage() {
  return (
    <>
      <section className="page-heading" aria-labelledby="page-title">
        <h1 id="page-title">بازیابی رمز عبور</h1>
      </section>
      <ForgotPasswordForm />
    </>
  );
}
