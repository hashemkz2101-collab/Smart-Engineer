"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

import { api, toApiError } from "../lib/api";
import { formatDate, projectTypeLabels } from "../lib/messages";
import type { Organization, Project } from "../lib/types";
import { useResource } from "../lib/use-resource";
import { FormError, FormField } from "./form-field";

function CreateProjectForm({ organizations }: { organizations: Organization[] }) {
  const router = useRouter();
  const [organizationId, setOrganizationId] = useState(organizations[0]?.id ?? "");
  const [name, setName] = useState("");
  const [projectType, setProjectType] = useState("residential_house");
  const [description, setDescription] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const created = await api.post<{ project: Project }>("/projects", {
        organization_id: organizationId,
        name,
        project_type: projectType,
        description: description || null,
      });
      router.push(`/projects/${created.project.id}`);
    } catch (failure) {
      setError(toApiError(failure).userMessage);
      setBusy(false);
    }
  }

  return (
    <form className="form-panel" onSubmit={submit} noValidate aria-labelledby="create-title">
      <h2 id="create-title">پروژهٔ تازه</h2>
      {organizations.length > 1 ? (
        <FormField id="create-org" label="سازمان">
          <select
            id="create-org"
            value={organizationId}
            onChange={(event) => setOrganizationId(event.target.value)}
          >
            {organizations.map((organization) => (
              <option key={organization.id} value={organization.id}>
                {organization.name}
              </option>
            ))}
          </select>
        </FormField>
      ) : null}
      <FormField id="create-name" label="نام پروژه">
        <input
          id="create-name"
          type="text"
          required
          maxLength={200}
          value={name}
          onChange={(event) => setName(event.target.value)}
        />
      </FormField>
      <FormField id="create-type" label="نوع پروژه">
        <select
          id="create-type"
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
      <FormField id="create-description" label="توضیحات (اختیاری)">
        <textarea
          id="create-description"
          rows={3}
          maxLength={5000}
          value={description}
          onChange={(event) => setDescription(event.target.value)}
        />
      </FormField>
      <FormError message={error} />
      <button className="button" type="submit" disabled={busy || !organizationId}>
        {busy ? "در حال ایجاد…" : "ایجاد پروژه"}
      </button>
    </form>
  );
}

export function ProjectsView() {
  const [archived, setArchived] = useState(false);
  const projects = useResource<{ projects: Project[] }>(
    `/projects?archived=${archived ? "true" : "false"}`,
  );
  const organizations = useResource<{ organizations: Organization[] }>("/orgs");

  return (
    <>
      <section className="page-heading" aria-labelledby="page-title">
        <h1 id="page-title">پروژه‌ها</h1>
        <p className="page-description">
          فقط پروژه‌هایی را می‌بینید که در آن‌ها نقشی دارید.
        </p>
      </section>

      <div className="tabs" role="group" aria-label="وضعیت پروژه‌ها">
        <button
          type="button"
          className="tab"
          aria-pressed={!archived}
          onClick={() => setArchived(false)}
        >
          فعال
        </button>
        <button
          type="button"
          className="tab"
          aria-pressed={archived}
          onClick={() => setArchived(true)}
        >
          بایگانی‌شده
        </button>
      </div>

      <section aria-label="فهرست پروژه‌ها">
        {projects.loading ? (
          <p className="status-text" role="status">
            در حال بارگذاری…
          </p>
        ) : projects.error ? (
          <p className="alert alert-error" role="alert">
            {projects.error.userMessage}
          </p>
        ) : projects.data && projects.data.projects.length > 0 ? (
          <ul className="card-list">
            {projects.data.projects.map((project) => (
              <li key={project.id} className="card">
                <h2>
                  <Link href={`/projects/${project.id}`}>{project.name}</Link>
                </h2>
                <p className="card-meta">
                  {projectTypeLabels[project.project_type] ?? project.project_type} ·{" "}
                  {formatDate(project.created_at)}
                </p>
              </li>
            ))}
          </ul>
        ) : (
          <p className="status-text">
            {archived ? "پروژهٔ بایگانی‌شده‌ای وجود ندارد." : "هنوز پروژه‌ای ندارید."}
          </p>
        )}
      </section>

      {!archived && organizations.data && organizations.data.organizations.length > 0 ? (
        <CreateProjectForm organizations={organizations.data.organizations} />
      ) : null}
    </>
  );
}
