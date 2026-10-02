# Thisissus 💌

Our self-hosted dashboard for dates, date ideas and recipes. Spec: PRD issue #1; work is split into issues #2–#37.

- **Backend:** FastAPI + asyncpg (hand-written SQL), Postgres 17
- **Frontend:** React + Vite (plain JS) + Tailwind v4
- **Original invite page:** `docs/reference/invite-original.html`

## Setup (Windows, local Postgres)

1. Copy `.env.example` to `.env` and set `DB_PASSWORD`.
2. Create the DB role (it needs `CREATEDB` because the tests create `thisissus_test`). In psql as `postgres`:
   ```sql
   CREATE ROLE thisissus LOGIN CREATEDB PASSWORD '...';
   CREATE DATABASE thisissus OWNER thisissus;
   ```
3. Backend:
   ```bash
   cd backend
   python -m venv .venv
   .venv/Scripts/python -m pip install -e ".[dev]"
   ```
4. Frontend:
   ```bash
   cd frontend
   npm install
   ```

## Run

```bash
cd backend && .venv/Scripts/python -m uvicorn app.main:app --port 8000   # restart after backend changes (--reload hangs on Windows)
cd backend && .venv/Scripts/python -m app.worker                  # background jobs (media, push, reminders)
cd frontend && npm run dev     # http://localhost:5173, proxies /api to :8000
```

## First admin

```bash
cd backend && .venv/Scripts/python -m app.cli bootstrap-admin "Your name"
```
Open the printed `/invite/<token>` link (valid 7 days, single use) and create a passkey. Later, log in at `/login`.
Set a fallback PIN under Settings. Unlock a locked PIN: `.venv/Scripts/python -m app.cli unlock <username>`.
Passkeys are bound to `RP_ID`/`ORIGIN` from `.env`, so ones made on `localhost` don't work on the production domain.

## Test

```bash
cd backend && .venv/Scripts/python -m pytest
cd frontend && npm test
```
Tests drop and recreate `thisissus_test`, build it with the real migrations, and roll back each test's transaction.

## Database changes

Add a new file to `backend/migrations/` with the next number, e.g. `002_tags.sql`. The API applies new files at startup, one transaction per file, and records them in `schema_migrations`. **Never edit a file that has already run.**
