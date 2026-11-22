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

export type ProjectInvitation = {
  id: string;
  email: string;
  role: string;
  expires_at: string;
};

export type ActivityEvent = {
  id: number;
  action: string;
  actor_user_id: string;
  target_user_id: string | null;
  detail: Record<string, unknown> | null;
  created_at: string;
};

export type AdminUser = {
  id: string;
  email: string;
  display_name: string;
  is_active: boolean;
  is_system_admin: boolean;
  last_login_at: string | null;
  created_at: string | null;
};

export type AdminProject = {
  id: string;
  name: string;
  project_type: string;
  status: "active" | "archived";
  organization_id: string;
  organization_name: string;
  member_count: number;
  created_at: string | null;
};

export type AdminAuditEvent = {
  id: number;
  action: string;
  actor_email: string | null;
  target_email: string | null;
  target_project_id: string | null;
  detail: Record<string, unknown> | null;
  created_at: string | null;
};
