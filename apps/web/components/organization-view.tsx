"use client";

import { useState, type FormEvent } from "react";

import { api, toApiError } from "../lib/api";
import { orgRoleLabels } from "../lib/messages";
import type { OrgMember, Organization } from "../lib/types";
import { useResource } from "../lib/use-resource";
import { FormError, FormField } from "./form-field";

function OrganizationDetail({ organization }: { organization: Organization }) {
  const [version, setVersion] = useState(0);
  const members = useResource<{ members: OrgMember[] }>(
    `/orgs/${organization.id}/members`,
    version,
  );
  const [email, setEmail] = useState("");
  const [role, setRole] = useState("member");
  const [error, setError] = useState<string | null>(null);
  const [inviteLink, setInviteLink] = useState<string | null>(null);
  const [pendingRemoval, setPendingRemoval] = useState<string | null>(null);

  const canInvite = organization.org_role === "owner" || organization.org_role === "admin";
  const isOwner = organization.org_role === "owner";

  async function run(action: () => Promise<unknown>) {
    setError(null);
    try {
      await action();
      setVersion((current) => current + 1);
    } catch (failure) {
      setError(toApiError(failure).userMessage);
    }
  }

  async function invite(event: FormEvent) {
    event.preventDefault();
    setInviteLink(null);
    await run(async () => {
      const result = await api.post<{ token: string }>(
        `/orgs/${organization.id}/invitations`,
        { email, org_role: role },
      );
      setInviteLink(
        `${window.location.origin}/invitations/accept?token=${encodeURIComponent(result.token)}`,
      );
      setEmail("");
    });
  }

  return (
    <>
      <section className="detail-section" aria-labelledby="members-title">
        <h2 id="members-title">اعضای سازمان</h2>
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
              <div className="row-actions">
                {isOwner && member.org_role !== "owner" ? (
                  <select
                    aria-label={`نقش ${member.display_name}`}
                    value={member.org_role}
                    onChange={(event) =>
                      run(() =>
                        api.patch(`/orgs/${organization.id}/members/${member.user_id}`, {
                          org_role: event.target.value,
                        }),
                      )
                    }
                  >
                    <option value="admin">{orgRoleLabels.admin}</option>
                    <option value="member">{orgRoleLabels.member}</option>
                  </select>
                ) : (
                  <span className="badge">{orgRoleLabels[member.org_role]}</span>
                )}
                {canInvite && member.org_role !== "owner" ? (
                  pendingRemoval === member.user_id ? (
                    <button
                      type="button"
                      className="button button-danger"
                      onClick={() => {
                        setPendingRemoval(null);
                        void run(() =>
                          api.delete(`/orgs/${organization.id}/members/${member.user_id}`),
                        );
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
                  )
                ) : null}
              </div>
            </li>
          ))}
        </ul>
        <FormError message={error} />
      </section>

      {canInvite ? (
        <form className="form-panel" onSubmit={invite} noValidate aria-labelledby="invite-title">
          <h2 id="invite-title">دعوت عضو</h2>
          <p className="field-hint">
            ارسال ایمیل هنوز فعال نیست؛ پس از ساخت دعوت، پیوند را خودتان برای فرد
            دعوت‌شده بفرستید. این پیوند فقط یک بار نمایش داده می‌شود و ۷ روز اعتبار دارد.
          </p>
          <FormField id="invite-email" label="ایمیل فرد دعوت‌شده">
            <input
              id="invite-email"
              type="email"
              dir="ltr"
              required
              value={email}
              onChange={(event) => setEmail(event.target.value)}
            />
          </FormField>
          <FormField id="invite-role" label="نقش در سازمان">
            <select id="invite-role" value={role} onChange={(event) => setRole(event.target.value)}>
              <option value="member">{orgRoleLabels.member}</option>
              {isOwner ? <option value="admin">{orgRoleLabels.admin}</option> : null}
            </select>
          </FormField>
          <button className="button" type="submit">
            ساخت دعوت‌نامه
          </button>
          {inviteLink ? (
            <div role="status" className="alert alert-success">
              <label htmlFor="invite-link">پیوند دعوت:</label>
              <input id="invite-link" type="text" dir="ltr" readOnly value={inviteLink} />
            </div>
          ) : null}
        </form>
      ) : null}
    </>
  );
}

export function OrganizationView() {
  const organizations = useResource<{ organizations: Organization[] }>("/orgs");
  const [selected, setSelected] = useState<string | null>(null);

  const list = organizations.data?.organizations ?? [];
  const current = list.find((organization) => organization.id === selected) ?? list[0];

  return (
    <>
      <section className="page-heading" aria-labelledby="page-title">
        <h1 id="page-title">سازمان</h1>
        <p className="page-description">
          اعضای سازمان را ببینید و کسانی را برای همکاری دعوت کنید. نقش هر فرد در
          هر پروژه جداگانه در همان پروژه تعیین می‌شود.
        </p>
      </section>

      {organizations.loading ? (
        <p className="status-text" role="status">
          در حال بارگذاری…
        </p>
      ) : organizations.error ? (
        <p className="alert alert-error" role="alert">
          {organizations.error.userMessage}
        </p>
      ) : current ? (
        <>
          {list.length > 1 ? (
            <FormField id="org-select" label="سازمان">
              <select
                id="org-select"
                value={current.id}
                onChange={(event) => setSelected(event.target.value)}
              >
                {list.map((organization) => (
                  <option key={organization.id} value={organization.id}>
                    {organization.name} ({orgRoleLabels[organization.org_role]})
                  </option>
                ))}
              </select>
            </FormField>
          ) : (
            <p className="card-meta">
              {current.name} · نقش شما: {orgRoleLabels[current.org_role]}
            </p>
          )}
          <OrganizationDetail key={current.id} organization={current} />
        </>
      ) : (
        <p className="status-text">سازمانی پیدا نشد.</p>
      )}
    </>
  );
}
