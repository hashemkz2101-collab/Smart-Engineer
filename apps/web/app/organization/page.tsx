import type { Metadata } from "next";

import { OrganizationView } from "../../components/organization-view";
import { RequireAuth } from "../../components/require-auth";

export const metadata: Metadata = { title: "سازمان | Smart Engineer" };

export default function OrganizationPage() {
  return (
    <RequireAuth>
      <OrganizationView />
    </RequireAuth>
  );
}
