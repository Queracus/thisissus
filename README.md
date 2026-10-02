# Thisissus 💌

Our self-hosted dashboard for dates, date ideas and recipes, for a couple and later family and friends.
Spec: PRD issue #1; work is split into issues #2–#37.

## What it does

- **Dates We've Had:** time/place/map pin, photos and videos, each partner's rating, notes and "would do again", tags, cost, filters, map, "On this day".
- **Date Ideas:** the original "Greva na …?" invite becomes the way to add an idea. Proposing 1–3 times leads to accept / refuse / counter, then **scheduled**, then **"Šla sva!"**, which creates a pre-filled date. Also a "Surprise us" picker and a calendar.
- **Recipes:** ingredients, steps, photos, ratings, "Skuhala sva!", import from a URL, servings scaling, a shared shopping list.
- **Spaces & sharing:** content belongs to a space (e.g. "Midva"). Share one item or a whole section read-only, with an account or through a secret link that expires (1h/1d/1w).
- **Notifications:** a bell plus phone push (PWA), and reminders the day before a date and for unrated dates and recipes.
- **Safety:** passkey login with a PIN fallback, a 30-day trash, nightly backups to USB, and a photo export to plain folders.

## Stack

- **Backend:** FastAPI + asyncpg (hand-written SQL), Postgres 17; everything, photos and videos included, lives in Postgres.
- **Worker:** same codebase, `python -m app.worker`: photo/video processing, push, reminders, trash purge, photo export.
- **Frontend:** React + Vite (plain JS) + Tailwind v4, an installable PWA.
- **Original invite page:** `docs/reference/invite-original.html`

```
backend/app/        FastAPI app: routers/, auth/, media/, policy.py (who may see what), sharing.py, proposals.py (state machine), jobs.py, worker.py
backend/migrations/ numbered SQL files, applied automatically
backend/tests/      pytest (real Postgres test database)
frontend/src/       pages/, components/, i18n/ (sl + en), sw.js (service worker)
ops/backup.sh       nightly backup
docker-compose.yml  production stack
```

## Prerequisites

| Tool | Version | Windows | Linux (Debian/Ubuntu) |
|---|---|---|---|
| Python | 3.12+ | python.org installer | `sudo apt install python3 python3-venv` |
| Node.js | 20+ | nodejs.org installer | `sudo apt install nodejs npm` (or nodesource) |
| PostgreSQL | 17 | EnterpriseDB installer | `sudo apt install postgresql-17` (PGDG repo) |
| ffmpeg | any recent | `winget install Gyan.FFmpeg` | `sudo apt install ffmpeg` |

`ffmpeg` and `ffprobe` must be on your `PATH`. The worker uses them to convert videos (HEVC → H.264) and make posters.
Photos need nothing extra: Pillow and pillow-heif ship as Python wheels.

**Windows + Postgres:** exclude `C:\Program Files\PostgreSQL\17\data` from antivirus real-time scanning
(Windows Security → Virus & threat protection → Exclusions). A scanner that locks a database file can make Postgres crash.

In the commands below, `PY` is the virtualenv's Python:

| | Windows | Linux |
|---|---|---|
| `PY` | `.venv\Scripts\python` | `.venv/bin/python` |

## Setup

1. Copy `.env.example` to `.env` and set `DB_PASSWORD` (any long random string).
2. Create the DB role and database. The role needs `CREATEDB` because the tests create `thisissus_test`.
   - Windows: `"C:\Program Files\PostgreSQL\17\bin\psql.exe" -U postgres -h localhost`
   - Linux: `sudo -u postgres psql`

   ```sql
   CREATE ROLE thisissus LOGIN CREATEDB PASSWORD '<same as DB_PASSWORD>';
   CREATE DATABASE thisissus OWNER thisissus;
   ```
3. Backend:
   ```bash
   cd backend
   python -m venv .venv          # Linux: python3 -m venv .venv
   PY -m pip install -e ".[dev]"
   PY -m app.cli vapid-keys      # paste the two lines into .env (needed for push notifications)
   ```
4. Frontend:
   ```bash
   cd frontend
   npm install
   ```

## Run (development)

Three terminals:

```bash
cd backend && PY -m uvicorn app.main:app --port 8000
cd backend && PY -m app.worker
cd frontend && npm run dev        # http://localhost:5173, proxies /api to :8000
```

Restart uvicorn after backend changes (`--reload` hangs on Windows; on Linux `--reload --reload-dir app` works).
The API and the worker both apply new migrations on start.

## First admin

```bash
cd backend && PY -m app.cli bootstrap-admin "Your name"
```
This creates you as admin and as owner of a first space, "Midva". Open the printed `/invite/<token>` link (valid 7 days, single use) and create a passkey. After that, log in at `/login`.
Invite your partner from the **Prostor** page ("Povabi novo osebo").

- Set a fallback PIN under Settings.
- Unlock a locked PIN: `PY -m app.cli unlock <username>` (or "Odkleni PIN" in the admin panel).
- Passkeys are bound to `RP_ID`/`ORIGIN` from `.env`. Ones made on `localhost` don't work on the production domain.

## CLI

| Command | What it does |
|---|---|
| `PY -m app.cli bootstrap-admin "<name>"` | new admin user (owner of space "Midva") + one-time invite link |
| `PY -m app.cli unlock <username>` | clear a PIN lockout |
| `PY -m app.cli vapid-keys` | print new web-push keys for `.env` |

## Configuration (`.env`)

| Key | Meaning |
|---|---|
| `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME` | Postgres connection |
| `DB_TEST_NAME` | test database (reused, schema recreated each run) |
| `RP_ID`, `ORIGIN` | passkey domain + site URL: `localhost` / `http://localhost:5173` in dev, the `.si` domain in production |
| `COOKIE_SECURE` | `1` in production (HTTPS-only session cookie) |
| `VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY`, `VAPID_SUBJECT` | web push keys (`app.cli vapid-keys`) and a contact for push services |
| `TIMEZONE` | for "today", "On this day" and stats (default `Europe/Ljubljana`) |
| `EXPORT_DIR` | where the photo export goes (default `./export`) |
| `BACKUP_DIR` | where `ops/backup.sh` writes dumps + `backup-status.json` (the USB drive) |
| `CLOUDFLARE_TUNNEL_TOKEN`, `EXPORT_HOST_DIR` | Docker deploy only |

`.env` is never committed; `.env.example` lists every key.

## Test

```bash
cd backend && PY -m pytest
cd frontend && npm test
```
The backend tests reuse `thisissus_test` (its schema is recreated each run), build it with the real migrations, and roll back each test's transaction.
Video tests are skipped automatically if `ffmpeg` isn't on the `PATH`; backup-script tests need `bash` (Git Bash on Windows) and `pg_dump`.

## Backups

`ops/backup.sh` makes a full `pg_dump` (everything, photos and videos included), verifies it, keeps the newest 2, and writes
`backup-status.json` that the admin panel shows (last run, size, USB fill level, warnings).

```bash
BACKUP_DIR=/mnt/usb/thisissus ops/backup.sh
```

On the server (Linux), once:

1. Find the USB drive's UUID: `lsblk -f`. Mount it permanently: add to `/etc/fstab`
   `UUID=<uuid>  /mnt/usb  ext4  defaults,nofail  0  2`, then `sudo mkdir -p /mnt/usb && sudo mount -a`.
2. Set `BACKUP_DIR=/mnt/usb/thisissus` in `.env` (the admin panel reads the status file from there too).
3. Nightly at 03:00: `crontab -e` →
   `0 3 * * * cd /path/to/thisissus && BACKUP_DIR=/mnt/usb/thisissus ops/backup.sh >> /var/log/thisissus-backup.log 2>&1`

**Restore** (test this once before trusting it):

```bash
createdb -U thisissus thisissus_restored
pg_restore -U thisissus -d thisissus_restored --no-owner /mnt/usb/thisissus/thisissus-<newest>.dump
```
Point `DB_NAME` at `thisissus_restored` (or rename the databases), start the app, and check a few dates and photos.

**Photo export:** Admin → "Izvoz fotk" writes every original photo and video into `EXPORT_DIR/<space>/zmenki/YYYY/MM/<date>/…`
and `…/recepti/<recipe>/…`. That way your photos are readable even without the app. Re-runs only add what's new.

## Database changes

Add a new file to `backend/migrations/` with the next number (the latest is `024_export_runs.sql`, so the next is `025_<what>.sql`).
New files are applied at startup, one transaction per file, and recorded in `schema_migrations`. **Never edit a file that has already run.**

## Deploy (home server, Ubuntu + Docker)

> The Docker files are written but have **not been run yet** (issue #36). Expect small fixes on the first `docker compose up`.

1. Install Docker (`curl -fsSL https://get.docker.com | sh`) and the Postgres 17 client for backups (`apt install postgresql-client-17`).
2. Cloudflare: add the `.si` domain (move its nameservers to Cloudflare), then Zero Trust → Networks → Tunnels → create a tunnel,
   copy its token, and add a public hostname `yourdomain.si` → service `http://web:80`.
3. `git clone` the repo, `cp .env.example .env` and fill in:
   `DB_PASSWORD`, `RP_ID=yourdomain.si`, `ORIGIN=https://yourdomain.si`, `COOKIE_SECURE=1`, new `VAPID_*` keys
   (`docker compose run --rm api python -m app.cli vapid-keys`), `CLOUDFLARE_TUNNEL_TOKEN`, `BACKUP_DIR`.
4. `docker compose up -d --build`, then `docker compose exec api python -m app.cli bootstrap-admin "Your name"` and open the link on your phone.
5. Updates: `git pull && docker compose up -d --build` (migrations run automatically on start).

Postgres listens only on `127.0.0.1:5432` (for `ops/backup.sh` on the host); the internet only reaches the app through the tunnel.

## Things only you can do

- [ ] Install the prerequisites above (including `ffmpeg`) on every machine that runs the app.
- [ ] Run `bootstrap-admin` once and register your passkey (Windows Hello / phone).
- [ ] Backups (#35): mount the USB drive, set `BACKUP_DIR`, add the cron line, do one test restore (see Backups).
- [ ] Deploy (#36): buy the `.si` domain, move its nameservers to Cloudflare, create the tunnel token, install Ubuntu Server + Docker on the ProDesk, first `docker compose up`.
- [ ] Go-live (#37): production `.env` (`RP_ID`, `ORIGIN`, `COOKIE_SECURE=1`, new VAPID keys), register passkeys on the real domain,
      turn on notifications on both phones (iPhone: Share → Add to Home Screen first), check video playback, do the restore drill.
