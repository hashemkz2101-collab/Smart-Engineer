import type { Metadata } from "next";

import { ResetPasswordForm } from "../../components/reset-password-form";

export const metadata: Metadata = { title: "رمز عبور تازه | Smart Engineer" };

export default async function ResetPasswordPage({
  searchParams,
}: {
  searchParams: Promise<{ token?: string }>;
}) {
  const { token } = await searchParams;
  return (
    <>
      <section className="page-heading" aria-labelledby="page-title">
        <h1 id="page-title">تعیین رمز عبور تازه</h1>
      </section>
      <ResetPasswordForm token={token} />
    </>
  );
}
