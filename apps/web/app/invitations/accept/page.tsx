import type { Metadata } from "next";

import { AcceptInvitation } from "../../../components/accept-invitation";
import { RequireAuth } from "../../../components/require-auth";

export const metadata: Metadata = { title: "پذیرش دعوت | Smart Engineer" };

export default async function AcceptInvitationPage({
  searchParams,
}: {
  searchParams: Promise<{ token?: string }>;
}) {
  const { token } = await searchParams;
  return (
    <RequireAuth>
      <section className="page-heading" aria-labelledby="page-title">
        <h1 id="page-title">پذیرش دعوت</h1>
      </section>
      <AcceptInvitation token={token} />
    </RequireAuth>
  );
}
