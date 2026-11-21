// A tiny in-browser fake of the Smart Engineer API for UI tests. Requests are
// intercepted by Playwright, so these tests verify the interface (forms, redirects,
// messages, CSRF header use, accessibility), NOT the real backend: the backend has
// its own tests and a full web+API run against a real database is a separate check.

export const USER = {
  id: "u-1",
  email: "ali@example.com",
  display_name: "علی رضایی",
  is_system_admin: false,
};
export const ORG = { id: "o-1", name: "علی رضایی", org_role: "owner" };
export const PROJECT = {
  id: "p-1",
  organization_id: "o-1",
  name: "ویلای نمونه",
  project_type: "residential_house",
  status: "active",
  description: null,
  created_at: "2026-11-20T10:00:00+00:00",
  archived_at: null,
};
export const OWNER_PERMISSIONS = [
  "project.view",
  "project.intake.edit",
  "project.site.edit",
  "project.update",
  "project.archive",
  "project.restore",
  "project.members.manage",
];

const json = (route, status, body) =>
  route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) });

export const error = (code, message = "x") => ({
  error: { code, message, correlation_id: "test" },
});

/**
 * Installs the fake API. `state.loggedIn` controls /auth/me. `overrides` maps
 * "METHOD /path" to (route, request) => boolean (true when handled).
 */
export async function mockApi(page, state = {}, overrides = {}) {
  const seen = (state.requests = state.requests ?? []);
  await page.route("**/api/v1/**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const path = url.pathname.replace("/api/v1", "");
    const key = `${request.method()} ${path}`;
    seen.push({
      key,
      query: url.search,
      headers: request.headers(),
      body: request.postData() ? JSON.parse(request.postData()) : null,
    });

    if (overrides[key] && (await overrides[key](route, request))) return;

    switch (key) {
      case "GET /auth/me":
        return state.loggedIn
          ? json(route, 200, { user: USER, csrf_token: "csrf-1" })
          : json(route, 401, error("http_401"));
      case "POST /auth/register":
        return json(route, 201, { user: USER });
      case "POST /auth/login":
        state.loggedIn = true;
        return json(route, 200, { user: USER, csrf_token: "csrf-1" });
      case "POST /auth/logout":
        state.loggedIn = false;
        return route.fulfill({ status: 204 });
      case "POST /auth/password-reset/request":
        return json(route, 202, { status: "accepted" });
      case "GET /orgs":
        return json(route, 200, { organizations: [ORG] });
      case "GET /projects":
        return json(route, 200, { projects: state.projects ?? [] });
      case "POST /projects":
        return json(route, 201, { project: PROJECT });
      case `GET /projects/${PROJECT.id}`:
        return json(route, 200, {
          project: state.project ?? PROJECT,
          my_role: "owner",
          permissions: state.permissions ?? OWNER_PERMISSIONS,
        });
      case `GET /projects/${PROJECT.id}/members`:
        return json(route, 200, {
          members: [
            { user_id: USER.id, email: USER.email, display_name: USER.display_name, role: "owner" },
          ],
        });
      case `GET /projects/${PROJECT.id}/activity`:
        return json(route, 200, {
          events: [
            {
              id: 1,
              action: "project.created",
              actor_user_id: USER.id,
              target_user_id: null,
              detail: null,
              created_at: PROJECT.created_at,
            },
          ],
        });
      case `GET /projects/${PROJECT.id}/intake`:
        return json(route, 200, {
          steps: ["identity", "location", "people", "legal"].map((step) => ({
            step,
            data: state.intake?.[step]?.data ?? {},
            complete: state.intake?.[step]?.complete ?? false,
            missing: [],
            version: state.intake?.[step]?.version ?? 0,
            updated_at: null,
          })),
        });
      case `GET /projects/${PROJECT.id}/site`:
        return json(route, 200, {
          sections: ["parcel", "access", "terrain", "surroundings", "soil"].map((section) => {
            const saved = state.site?.[section];
            const base = {
              section,
              data: saved?.data ?? {},
              complete: saved?.complete ?? false,
              missing: [],
              not_provided: saved?.not_provided ?? [],
              version: saved?.version ?? 0,
              updated_at: null,
            };
            return section === "parcel"
              ? {
                  ...base,
                  derived: saved?.derived ?? {
                    status: "not_computable",
                    computed_area_m2: null,
                    declared_area_m2: null,
                    difference_m2: null,
                    difference_percent: null,
                    tolerance_percent: 1,
                    computed_side_lengths_m: [],
                  },
                }
              : base;
          }),
        });
      case "GET /orgs/o-1/members":
        return json(route, 200, {
          members: [
            { user_id: USER.id, email: USER.email, display_name: USER.display_name, org_role: "owner" },
          ],
        });
      default:
        return json(route, 404, error("http_404"));
    }
  });
}
