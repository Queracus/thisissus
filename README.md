# Thisissus 💌

Our self-hosted dashboard for dates, date ideas and recipes. Spec: PRD issue #1; work is split into issues #2–#37.

- **Backend:** FastAPI + asyncpg (hand-written SQL), Postgres 17
- **Worker:** same codebase, `python -m app.worker` (photo/video processing, push, reminders)
- **Frontend:** React + Vite (plain JS) + Tailwind v4
- **Original invite page:** `docs/reference/invite-original.html`

## Prerequisites

| Tool | Version | Windows | Linux (Debian/Ubuntu) |
|---|---|---|---|
| Python | 3.12+ | python.org installer | `sudo apt install python3 python3-venv` |
| Node.js | 20+ | nodejs.org installer | `sudo apt install nodejs npm` (or nodesource) |
| PostgreSQL | 17 | EnterpriseDB installer | `sudo apt install postgresql-17` (PGDG repo) |
| ffmpeg | any recent | `winget install Gyan.FFmpeg` | `sudo apt install ffmpeg` |

`ffmpeg` and `ffprobe` must be on your `PATH`. The worker uses them to convert videos (HEVC → H.264) and make posters.
Photos need nothing extra: Pillow and pillow-heif ship as Python wheels.

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

- Set a fallback PIN under Settings.
- Unlock a locked PIN: `PY -m app.cli unlock <username>` (or "Odkleni PIN" in the admin panel).
- Passkeys are bound to `RP_ID`/`ORIGIN` from `.env`. Ones made on `localhost` don't work on the production domain.

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

## Database changes

Add a new file to `backend/migrations/` with the next number, e.g. `013_video.sql`. New files are applied at startup, one transaction per file, and recorded in `schema_migrations`. **Never edit a file that has already run.**

## Things only you can do

- [ ] Install the prerequisites above (including `ffmpeg`) on every machine that runs the app.
- [ ] Run `bootstrap-admin` once and register your passkey (Windows Hello / phone).
- [ ] Backups (#35): mount the USB drive, set `BACKUP_DIR`, add the cron line, do one test restore (see Backups).
- [ ] Production (#36–#37): buy the `.si` domain, move its nameservers to Cloudflare, create a Cloudflare Tunnel token, install Ubuntu Server + Docker on the ProDesk.
- [ ] In production `.env`: `RP_ID=<domain>`, `ORIGIN=https://<domain>`, `COOKIE_SECURE=1`, then register passkeys again on the real domain.
