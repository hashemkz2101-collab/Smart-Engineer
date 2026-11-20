import type { Metadata } from "next";

import { ProjectsView } from "../../components/projects-view";
import { RequireAuth } from "../../components/require-auth";

export const metadata: Metadata = { title: "پروژه‌ها | Smart Engineer" };

export default function ProjectsPage() {
  return (
    <RequireAuth>
      <ProjectsView />
    </RequireAuth>
  );
}
