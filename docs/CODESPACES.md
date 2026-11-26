# Trying Smart Engineer in GitHub Codespaces

This starts the real application (web app + API + a throwaway database) in a Codespace so you
can open it from any browser, phone included, register, log in and use every implemented page.
It uses no paid service and no public deployment: the forwarded ports are **private** (only you,
signed in to GitHub, can open them). Codespaces itself uses your GitHub quota (free monthly
allowance, then billing if you enabled it), so stop or delete the Codespace when you are done.

## Start

1. On GitHub open the repository, **Code → Codespaces → Create codespace on main** (or on the
   branch you want to try). Choose a 4-core machine if offered; 2 cores also work but are slower.
2. Wait for the first creation to finish (about 5–10 minutes): it installs Python 3.14, Node 24
   and the locked dependencies (`scripts/dev/setup.sh`), then starts everything
   (`scripts/dev/up.sh`) and prints the address.
3. Open the **Ports** tab, find port **3000** ("Smart Engineer (open this one)") and click the
   globe icon, or copy the address printed in the terminal. On a phone, open the same address in
   the phone browser and sign in to GitHub if asked.
4. Log in with a demo account (below) or use **register** to create your own.

If nothing is running (for example after the Codespace was stopped), run `scripts/dev/up.sh`.
Any time, `cat .dev/urls.txt` shows the address again.

## Demo accounts

Password for all (public, for this throwaway database only): `Demo Password 2026 Local`

| Email | Role |
|---|---|
| owner@demo.smart-engineer.test | owner of the demo organization and two sample projects |
| architect@demo.smart-engineer.test | architect |
| structural@demo.smart-engineer.test | structural engineer |
| qs@demo.smart-engineer.test | quantity surveyor (can mark the takeoff basis file version) |
| admin@demo.smart-engineer.test | system administrator (`/admin`) |

Emails are not really sent in this mode (the `.test` domain cannot receive mail); password reset
and invitation links are therefore not delivered. Invite by adding people who already have an
account, or accept invitations from the API.

## Choosing the database

```bash
scripts/dev/up.sh --db postgres   # default (PostgreSQL 17 in Docker)
scripts/dev/up.sh --db mysql      # MySQL 8.0 in Docker
scripts/dev/up.sh --db sqlite     # no Docker (used automatically if Docker is unavailable)
```

or set `SMART_ENGINEER_DEV_DB` before the start. The database is always one created by
`dev/docker-compose.yml` (or a SQLite file under `.dev/`); the script builds the URL itself and
ignores any `SMART_ENGINEER_DATABASE_URL` already set, and the demo seed refuses a non-local
database, so no real data can be touched. Switching engines starts from an empty database.

## Other commands

```bash
scripts/dev/up.sh --rebuild   # rebuild the web app after you change web code
scripts/dev/up.sh --web dev   # Next.js dev server with hot reload (slower first page load)
scripts/dev/down.sh           # stop the app (databases are stopped, data kept)
scripts/dev/down.sh --reset   # also delete the throwaway databases and demo files
tail -f .dev/api.log .dev/web.log
```

## How it is wired

The browser only talks to port 3000. The web app forwards `/api/*` to the API on
`127.0.0.1:8000` inside the Codespace, so cookies stay first-party and no CORS setup is needed.
The script sets `SMART_ENGINEER_ALLOWED_ORIGINS` to your Codespace address so the API's
cross-site check accepts the forwarded origin. Uploaded files go to `.dev/files`. Virus scanning
uses the built-in checks only (no ClamAV), which is acceptable for trials with test files only.

## Limits

- Not tested here: the Codespaces creation itself runs on GitHub, so the first start may need a
  fix; tell me the last lines of the creation log if it fails.
- Email delivery, ClamAV and payments are not available in this mode.
