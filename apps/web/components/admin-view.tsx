"use client";

import { useState, type FormEvent } from "react";

import { api, toApiError } from "../lib/api";
import { adminActionLabels, projectRoleLabels } from "../lib/messages";
import type { AdminAuditEvent, AdminProject, AdminUser, ProjectMember } from "../lib/types";
import { useResource } from "../lib/use-resource";
import { useAuth } from "./auth-provider";
import { FormError, FormField } from "./form-field";

type Tab = "users" | "projects" | "audit";

function useRunner(reload: () => void) {
  const [error, setError] = useState<string | null>(null);
  async function run(action: () => Promise<unknown>) {
    setError(null);
    try {
      await action();
      reload();
    } catch (failure) {
      setError(toApiError(failure).userMessage);
    }
  }
  return { error, run };
}

function UsersPanel({ selfId }: { selfId: string }) {
  const [version, setVersion] = useState(0);
  const [query, setQuery] = useState("");
  const [applied, setApplied] = useState("");
  const path = `/admin/users${applied ? `?q=${encodeURIComponent(applied)}` : ""}`;
  const users = useResource<{ users: AdminUser[] }>(path, version);
  const { error, run } = useRunner(() => setVersion((v) => v + 1));

  return (
    <section className="detail-section" aria-labelledby="admin-users-title">
      <h2 id="admin-users-title">کاربران</h2>
      <form
        className="inline-form"
        role="search"
        onSubmit={(event: FormEvent) => {
          event.preventDefault();
          setApplied(query.trim());
        }}
      >
        <FormField id="admin-user-query" label="جست‌وجوی کاربر">
          <input
            id="admin-user-query"
            type="search"
            dir="ltr"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
        </FormField>
        <button className="button" type="submit">جست‌وجو</button>
      </form>
      <FormError message={error ?? users.error?.userMessage ?? null} />
      <ul className="card-list">
        {users.data?.users.map((user) => (
          <li key={user.id} className="card member-row">
            <div>
              <strong>{user.display_name}</strong>
              <span className="card-meta" dir="ltr">{user.email}</span>
              <span className="card-meta">
                {user.is_active ? "فعال" : "غیرفعال"}
                {user.is_system_admin ? " · مدیر سیستم" : ""}
              </span>
            </div>
            {user.id === selfId ? (
              <span className="card-meta">حساب شما</span>
            ) : (
              <div className="row-actions">
                <button
                  className="button button-secondary"
                  type="button"
                  aria-label={`${user.is_active ? "غیرفعال‌سازی" : "فعال‌سازی"} ${user.display_name}`}
                  onClick={() =>
                    run(() => api.put(`/admin/users/${user.id}/active`, { active: !user.is_active }))
                  }
                >
                  {user.is_active ? "غیرفعال‌سازی" : "فعال‌سازی"}
                </button>
                <button
                  className="button button-secondary"
                  type="button"
                  aria-label={`${user.is_system_admin ? "گرفتن دسترسی مدیر از" : "دادن دسترسی مدیر به"} ${user.display_name}`}
                  onClick={() =>
                    run(() =>
                      api.put(`/admin/users/${user.id}/system-admin`, {
                        is_system_admin: !user.is_system_admin,
                      }),
                    )
                  }
                >
                  {user.is_system_admin ? "گرفتن دسترسی مدیر" : "دادن دسترسی مدیر"}
                </button>
              </div>
            )}
          </li>
        ))}
      </ul>
      {users.data && users.data.users.length === 0 ? (
        <p className="status-text">کاربری پیدا نشد.</p>
      ) : null}
    </section>
  );
}

function ProjectAccess({ project }: { project: AdminProject }) {
  const [version, setVersion] = useState(0);
  const members = useResource<{ members: ProjectMember[] }>(
    `/admin/projects/${project.id}/members`,
    version,
  );
  const [email, setEmail] = useState("");
  const [role, setRole] = useState("architect");
  const { error, run } = useRunner(() => setVersion((v) => v + 1));
  const archived = project.status === "archived";

  return (
    <div className="detail-section" role="group" aria-label={`دسترسی‌های ${project.name}`}>
      <FormError message={error ?? members.error?.userMessage ?? null} />
      <ul className="card-list">
        {members.data?.members.map((member) => (
          <li key={member.user_id} className="card member-row">
            <div>
              <strong>{member.display_name}</strong>
              <span className="card-meta" dir="ltr">{member.email}</span>
            </div>
            {archived ? (
              <span className="card-meta">{projectRoleLabels[member.role] ?? member.role}</span>
            ) : (
              <div className="row-actions">
                <select
                  aria-label={`نقش ${member.display_name} در ${project.name}`}
                  value={member.role}
                  onChange={(event) =>
                    run(() =>
                      api.patch(`/admin/projects/${project.id}/members/${member.user_id}`, {
                        role: event.target.value,
                      }),
                    )
                  }
                >
                  {Object.entries(projectRoleLabels)
                    .filter(([key]) => key !== "org_admin")
                    .map(([key, label]) => (
                      <option key={key} value={key}>{label}</option>
                    ))}
                </select>
                <button
                  className="button button-secondary"
                  type="button"
                  aria-label={`حذف ${member.display_name} از ${project.name}`}
                  onClick={() =>
                    run(() => api.delete(`/admin/projects/${project.id}/members/${member.user_id}`))
                  }
                >
                  حذف
                </button>
              </div>
            )}
          </li>
        ))}
      </ul>
      {archived ? (
        <p className="status-text">پروژهٔ بایگانی‌شده فقط‌خواندنی است.</p>
      ) : (
        <form
          className="inline-form"
          onSubmit={(event: FormEvent) => {
            event.preventDefault();
            run(async () => {
              await api.post(`/admin/projects/${project.id}/members`, { email, role });
              setEmail("");
            });
          }}
        >
          <FormField id={`add-email-${project.id}`} label={`ایمیل عضو جدید ${project.name}`}>
            <input
              id={`add-email-${project.id}`}
              type="email"
              dir="ltr"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
            />
          </FormField>
          <FormField id={`add-role-${project.id}`} label={`نقش عضو جدید ${project.name}`}>
            <select
              id={`add-role-${project.id}`}
              value={role}
              onChange={(event) => setRole(event.target.value)}
            >
              {Object.entries(projectRoleLabels)
                .filter(([key]) => key !== "org_admin")
                .map(([key, label]) => (
                  <option key={key} value={key}>{label}</option>
                ))}
            </select>
          </FormField>
          <button className="button" type="submit">افزودن عضو</button>
        </form>
      )}
    </div>
  );
}

function ProjectsPanel() {
  const projects = useResource<{ projects: AdminProject[] }>("/admin/projects");
  const [open, setOpen] = useState<string | null>(null);

  return (
    <section className="detail-section" aria-labelledby="admin-projects-title">
      <h2 id="admin-projects-title">پروژه‌ها و دسترسی‌ها</h2>
      <p className="status-text">
        فقط فراداده و دسترسی‌ها دیده می‌شود؛ محتوای پروژه برای مدیر سیستم باز نیست.
      </p>
      <FormError message={projects.error?.userMessage ?? null} />
      <ul className="card-list">
        {projects.data?.projects.map((project) => (
          <li key={project.id} className="card">
            <div className="member-row">
              <div>
                <strong>{project.name}</strong>
                <span className="card-meta">
                  {project.organization_name} · {project.member_count} عضو
                  {project.status === "archived" ? " · بایگانی‌شده" : ""}
                </span>
              </div>
              <button
                className="button button-secondary"
                type="button"
                aria-expanded={open === project.id}
                onClick={() => setOpen(open === project.id ? null : project.id)}
              >
                {open === project.id ? `بستن ${project.name}` : `مدیریت دسترسی ${project.name}`}
              </button>
            </div>
            {open === project.id ? <ProjectAccess project={project} /> : null}
          </li>
        ))}
      </ul>
      {projects.data && projects.data.projects.length === 0 ? (
        <p className="status-text">هنوز پروژه‌ای ثبت نشده است.</p>
      ) : null}
    </section>
  );
}

function AuditPanel() {
  const audit = useResource<{ events: AdminAuditEvent[] }>("/admin/audit?limit=100");
  return (
    <section className="detail-section" aria-labelledby="admin-audit-title">
      <h2 id="admin-audit-title">گزارش ممیزی</h2>
      <FormError message={audit.error?.userMessage ?? null} />
      <ul className="card-list">
        {audit.data?.events.map((event) => (
          <li key={event.id} className="card">
            <strong>{adminActionLabels[event.action] ?? event.action}</strong>
            <span className="card-meta" dir="ltr">
              {event.actor_email} → {event.target_email ?? "—"}
            </span>
            <span className="card-meta" dir="ltr">{event.created_at}</span>
          </li>
        ))}
      </ul>
      {audit.data && audit.data.events.length === 0 ? (
        <p className="status-text">رویدادی ثبت نشده است.</p>
      ) : null}
    </section>
  );
}

export function AdminView() {
  const { state } = useAuth();
  const [tab, setTab] = useState<Tab>("users");

  if (state.status !== "authenticated") return null;
  if (!state.user.is_system_admin) {
    return (
      <>
        <h1>صفحه پیدا نشد</h1>
        <p className="status-text">این صفحه وجود ندارد.</p>
      </>
    );
  }

  const tabs: { id: Tab; label: string }[] = [
    { id: "users", label: "کاربران" },
    { id: "projects", label: "پروژه‌ها" },
    { id: "audit", label: "ممیزی" },
  ];
  return (
    <>
      <h1>مدیریت سیستم</h1>
      <div role="group" aria-label="بخش‌های مدیریت" className="row-actions">
        {tabs.map((item) => (
          <button
            key={item.id}
            type="button"
            className={tab === item.id ? "button" : "button button-secondary"}
            aria-pressed={tab === item.id}
            onClick={() => setTab(item.id)}
          >
            {item.label}
          </button>
        ))}
      </div>
      {tab === "users" ? <UsersPanel selfId={state.user.id} /> : null}
      {tab === "projects" ? <ProjectsPanel /> : null}
      {tab === "audit" ? <AuditPanel /> : null}
    </>
  );
}
