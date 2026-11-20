import type { Metadata } from "next";

import { LoginForm } from "../../components/login-form";

export const metadata: Metadata = { title: "ورود | Smart Engineer" };

export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<{ next?: string }>;
}) {
  const { next } = await searchParams;
  return (
    <>
      <section className="page-heading" aria-labelledby="page-title">
        <h1 id="page-title">ورود به حساب</h1>
      </section>
      <LoginForm next={next} />
    </>
  );
}
