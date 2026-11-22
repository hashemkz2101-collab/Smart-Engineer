"use client";

import Link from "next/link";
import { useState, type FormEvent } from "react";

import { api, toApiError } from "../lib/api";
import {
  activityLabels,
  formatDate,
  projectRoleLabels,
  projectTypeLabels,
} from "../lib/messages";
import type { ActivityEvent, Project, ProjectMember } from "../lib/types";
import { useResource } from "../lib/use-resource";
import { FormError, FormField, FormNotice } from "./form-field";
import { IntakePanel } from "./intake-panel";
import { EnvironmentPanel } from "./environment-panel";
import { FilesPanel } from "./files-panel";
import { RequirementsPanel } from "./requirements-panel";
import { SitePanel } from "./site-panel";
import { ZoningPanel } from "./zoning-panel";

type ProjectResponse = { project: Project; my_role: string; permissions: string[] };

const assignableRoles = [
  "owner",
  "architect",
  "structural_engineer",
  "mep_engineer",
  "quantity_surveyor",
];

function RoleSelect({
  id,
  value,
  onChange,
  label,
}: {
  id: string;
  value: string;
  onChange: (role: string) => void;
  label: string;
}) {
  return (
    <select id={id} aria-label={label} value={value} onChange={(e) => onChange(e.target.value)}>
      {assignableRoles.map((role) => (
        <option key={role} value={role}>
          {projectRoleLabels[role]}
        </option>
      ))}
    </select>
  );
}

function EditForm({ project, onSaved }: { project: Project; onSaved: () => void }) {
  const [name, setName] = useState(project.name);
  const [projectType, setProjectType] = useState(project.project_type);
  const [description, setDescription] = useState(project.description ?? "");
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setNotice(null);
    try {
      await api.patch(`/projects/${project.id}`, {
        name,
        project_type: projectType,
        description,
      });
      setNotice("تغییرات ذخیره شد.");
      onSaved();
    } catch (failure) {
      setError(toApiError(failure).userMessage);
    }
  }

  return (
    <form className="form-panel" onSubmit={submit} noValidate aria-labelledby="edit-title">
      <h2 id="edit-title">ویرایش مشخصات</h2>
      <FormField id="edit-name" label="نام پروژه">
        <input
          id="edit-name"
          type="text"
          required
          maxLength={200}
          value={name}
          onChange={(event) => setName(event.target.value)}
        />
      </FormField>
      <FormField id="edit-type" label="نوع پروژه">
        <select
          id="edit-type"
          value={projectType}
          onChange={(event) => setProjectType(event.target.value)}
        >
          {Object.entries(projectTypeLabels).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
      </FormField>
      <FormField id="edit-description" label="توضیحات">
        <textarea
          id="edit-description"
          rows={3}
          maxLength={5000}
          value={description}
          onChange={(event) => setDescription(event.target.value)}
        />
      </FormField>
      <FormError message={error} />
      <FormNotice message={notice} />
      <button className="button" type="submit">
        ذخیرهٔ تغییرات
      </button>
    </form>
  );
}

function Members({
  projectId,
  canManage,
  version,
  onChanged,
}: {
  projectId: string;
  canManage: boolean;
  version: number;
  onChanged: () => void;
}) {
  const members = useResource<{ members: ProjectMember[] }>(
    `/projects/${projectId}/members`,
    version,
  );
  const [email, setEmail] = useState("");
  const [role, setRole] = useState("architect");
  const [error, setError] = useState<string | null>(null);
  const [pendingRemoval, setPendingRemoval] = useState<string | null>(null);

  async function run(action: () => Promise<unknown>) {
    setError(null);
    try {
      await action();
      onChanged();
    } catch (failure) {
      setError(toApiError(failure).userMessage);
    }
  }

  async function add(event: FormEvent) {
    event.preventDefault();
    await run(async () => {
      await api.post(`/projects/${projectId}/members`, { email, role });
      setEmail("");
    });
  }

  return (
    <section className="detail-section" aria-labelledby="members-title">
      <h2 id="members-title">اعضای پروژه</h2>
      {members.error ? (
        <p className="alert alert-error" role="alert">
          {members.error.userMessage}
        </p>
      ) : null}
      <ul className="card-list">
        {members.data?.members.map((member) => (
          <li key={member.user_id} className="card member-row">
            <div>
              <strong>{member.display_name}</strong>
              <span className="card-meta" dir="ltr">
                {member.email}
              </span>
            </div>
            {canManage ? (
              <div className="row-actions">
                <RoleSelect
                  id={`role-${member.user_id}`}
                  label={`نقش ${member.display_name}`}
                  value={member.role}
                  onChange={(next) =>
                    run(() => api.patch(`/projects/${projectId}/members/${member.user_id}`, { role: next }))
                  }
                />
                {pendingRemoval === member.user_id ? (
                  <button
                    type="button"
                    className="button button-danger"
                    onClick={() => {
                      setPendingRemoval(null);
                      void run(() => api.delete(`/projects/${projectId}/members/${member.user_id}`));
                    }}
                  >
                    تأیید حذف
                  </button>
                ) : (
                  <button
                    type="button"
                    className="button button-secondary"
                    onClick={() => setPendingRemoval(member.user_id)}
                  >
                    حذف
                  </button>
                )}
              </div>
            ) : (
              <span className="badge">{projectRoleLabels[member.role] ?? member.role}</span>
            )}
          </li>
        ))}
      </ul>
      <FormError message={error} />
      {canManage ? (
        <form className="form-panel" onSubmit={add} noValidate aria-labelledby="add-member-title">
          <h3 id="add-member-title">افزودن عضو</h3>
          <p className="field-hint">فقط کسی که عضو همین سازمان است اضافه می‌شود.</p>
          <FormField id="member-email" label="ایمیل عضو">
            <input
              id="member-email"
              type="email"
              dir="ltr"
              required
              value={email}
              onChange={(event) => setEmail(event.target.value)}
            />
          </FormField>
          <FormField id="member-role" label="نقش">
            <RoleSelect id="member-role" label="نقش" value={role} onChange={setRole} />
          </FormField>
          <button className="button" type="submit">
            افزودن
          </button>
        </form>
      ) : null}
    </section>
  );
}

function Activity({ projectId, version }: { projectId: string; version: number }) {
  const activity = useResource<{ events: ActivityEvent[] }>(
    `/projects/${projectId}/activity`,
    version,
  );
  return (
    <section className="detail-section" aria-labelledby="activity-title">
      <h2 id="activity-title">تاریخچهٔ فعالیت</h2>
      {activity.error ? (
        <p className="alert alert-error" role="alert">
          {activity.error.userMessage}
        </p>
      ) : null}
      <ol className="activity-list">
        {activity.data?.events.map((event) => (
          <li key={event.id}>
            <span>{activityLabels[event.action] ?? event.action}</span>
            <time className="card-meta" dateTime={event.created_at}>
              {formatDate(event.created_at)}
            </time>
          </li>
        ))}
      </ol>
    </section>
  );
}

export function ProjectDetail({ projectId }: { projectId: string }) {
  const [version, setVersion] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const resource = useResource<ProjectResponse>(`/projects/${projectId}`, version);
  const reload = () => setVersion((current) => current + 1);

  if (resource.loading) {
    return (
      <p className="status-text" role="status">
        در حال بارگذاری…
      </p>
    );
  }
  if (resource.error || !resource.data) {
    return (
      <>
        <p className="alert alert-error" role="alert">
          {resource.error?.userMessage ?? "خطایی رخ داد."}
        </p>
        <Link href="/projects">بازگشت به پروژه‌ها</Link>
      </>
    );
  }

  const { project, my_role: myRole, permissions } = resource.data;
  const can = (action: string) => permissions.includes(action);

  async function changeStatus(action: "archive" | "restore") {
    setError(null);
    try {
      await api.post(`/projects/${projectId}/${action}`);
      reload();
    } catch (failure) {
      setError(toApiError(failure).userMessage);
    }
  }

  return (
    <>
      <section className="page-heading" aria-labelledby="page-title">
        <p className="eyebrow">
          <Link href="/projects">پروژه‌ها</Link>
        </p>
        <h1 id="page-title">{project.name}</h1>
        <p className="page-description">
          {projectTypeLabels[project.project_type] ?? project.project_type} · نقش شما:{" "}
          {projectRoleLabels[myRole] ?? myRole}
        </p>
        {project.description ? <p>{project.description}</p> : null}
      </section>

      {project.status === "archived" ? (
        <p className="alert alert-notice" role="status">
          این پروژه بایگانی شده و فقط‌خواندنی است.
        </p>
      ) : null}
      <FormError message={error} />

      <div className="action-row">
        {can("project.archive") ? (
          <button type="button" className="button button-secondary" onClick={() => changeStatus("archive")}>
            بایگانی پروژه
          </button>
        ) : null}
        {can("project.restore") && project.status === "archived" ? (
          <button type="button" className="button" onClick={() => changeStatus("restore")}>
            بازگردانی از بایگانی
          </button>
        ) : null}
      </div>

      {can("project.update") ? <EditForm project={project} onSaved={reload} /> : null}

      {myRole === "org_admin" ? null : (
        <IntakePanel
          projectId={projectId}
          canEdit={can("project.intake.edit")}
          version={version}
        />
      )}

      {myRole === "org_admin" ? null : (
        <SitePanel
          projectId={projectId}
          canEdit={can("project.site.edit")}
          version={version}
        />
      )}

      {myRole === "org_admin" ? null : (
        <RequirementsPanel
          projectId={projectId}
          canEdit={can("project.requirements.edit")}
          version={version}
        />
      )}

      {myRole === "org_admin" ? null : (
        <EnvironmentPanel
          projectId={projectId}
          canEdit={can("project.environment.edit")}
          version={version}
        />
      )}

      {myRole === "org_admin" ? null : (
        <FilesPanel
          projectId={projectId}
          canUpload={can("project.files.upload")}
          canDelete={can("project.files.delete")}
          version={version}
        />
      )}

      {myRole === "org_admin" ? null : (
        <ZoningPanel
          projectId={projectId}
          canEdit={can("project.zoning.edit")}
          version={version}
        />
      )}

      {myRole === "org_admin" ? null : (
        <Members
          projectId={projectId}
          canManage={can("project.members.manage")}
          version={version}
          onChanged={reload}
        />
      )}
      {myRole === "org_admin" ? null : <Activity projectId={projectId} version={version} />}
    </>
  );
}
