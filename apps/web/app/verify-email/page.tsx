import type { Metadata } from "next";

import { VerifyEmailForm } from "../../components/verify-email-form";

export const metadata: Metadata = { title: "تأیید ایمیل | Smart Engineer" };

export default async function VerifyEmailPage({
  searchParams,
}: {
  searchParams: Promise<{ token?: string }>;
}) {
  const { token } = await searchParams;
  return (
    <>
      <section className="page-heading" aria-labelledby="page-title">
        <h1 id="page-title">تأیید ایمیل</h1>
      </section>
      <VerifyEmailForm token={token} />
    </>
  );
}
