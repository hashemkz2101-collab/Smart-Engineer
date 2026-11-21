export type User = {
  id: string;
  email: string;
  display_name: string;
  is_system_admin: boolean;
};

export type OrgRole = "owner" | "admin" | "member";

export type Organization = { id: string; name: string; org_role: OrgRole };

export type Project = {
  id: string;
  organization_id: string;
  name: string;
  project_type: string;
  status: "active" | "archived";
  description: string | null;
  created_at: string;
  archived_at: string | null;
};

export type OrgMember = {
  user_id: string;
  email: string;
  display_name: string;
  org_role: OrgRole;
};

export type ProjectMember = {
  user_id: string;
  email: string;
  display_name: string;
  role: string;
};

export type ActivityEvent = {
  id: number;
  action: string;
  actor_user_id: string;
  target_user_id: string | null;
  detail: Record<string, unknown> | null;
  created_at: string;
};
