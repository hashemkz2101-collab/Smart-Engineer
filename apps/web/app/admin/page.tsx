import type { Metadata } from "next";

import { AdminView } from "../../components/admin-view";
import { RequireAuth } from "../../components/require-auth";

export const metadata: Metadata = { title: "مدیریت سیستم | Smart Engineer" };

export default function AdminPage() {
  return (
    <RequireAuth>
      <AdminView />
    </RequireAuth>
  );
}
