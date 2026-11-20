import type { Metadata } from "next";

import { ProjectDetail } from "../../../components/project-detail";
import { RequireAuth } from "../../../components/require-auth";

export const metadata: Metadata = { title: "پروژه | Smart Engineer" };

export default async function ProjectPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return (
    <RequireAuth>
      <ProjectDetail projectId={id} />
    </RequireAuth>
  );
}
