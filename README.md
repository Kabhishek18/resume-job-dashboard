# Resume Job Dashboard

A full-stack MVP for scoring and tailoring resumes against job descriptions, running multi-portal job searches, and tracking applications—all behind email/password accounts.

---

## Contents

- [Features](#features)
- [Repository layout](#repository-layout)
- [Prerequisites](#prerequisites)
- [Quick start (local)](#quick-start-local)
- [Backend (FastAPI)](#backend-fastapi)
- [Frontend (Next.js)](#frontend-nextjs)
- [Configuration](#configuration)
- [API overview](#api-overview)
- [Testing](#testing)
- [Deployment](#deployment)
- [Troubleshooting](#troubleshooting)

---

## Features

**Resume**

- Paste or upload resume text (PDF, DOCX, TXT); semantic match scoring (`POST /api/match`, `/api/match/v2`).
- Guided wizard: fit analysis, tailoring, optional cover letter. Tailoring defaults to **stub**; optional **OpenRouter** LLM when configured.

**Jobs**

- Saved **search profiles** (keywords, locations, portals) and manual or scheduled runs.
- **Results** grid with filters, CSV/TSV export, optional match scoring when a profile resume is loaded.
- **Application board**: track statuses, notes, recruiter fields; remove entries without deleting aggregated listings.

**Account**

- Registration, login, profile (`GET/PATCH /api/profile`), saved resume (`PUT /api/profile/resume`), file extract (`POST /api/profile/resume-upload`).
- Settings UI: display name, password change, appearance (browser-only theme), resume editor.
- Password reset via email (transport configurable): `FORGOT`-style flow plus `RESET_TOKEN` handling—see [`backend-ai/.env.example`](backend-ai/.env.example).

**Dashboard**

- Summary counts by board status and recent board activity (`GET /api/dashboard/summary`).

---

## Repository layout

| Path | Role |
|------|------|
| [`backend-ai/`](backend-ai/) | FastAPI app, Alembic migrations, job collectors (JobSpy, Naukri, etc.). |
| [`frontend/`](frontend/) | Next.js App Router, Tailwind, shadcn-style UI; static-export friendly for GitHub Pages. |
| [`start.sh`](start.sh) | Local dev: conda Python 3.11 env, uvicorn `:8000`, `next dev` `:3000`. |
| [`render.yaml`](render.yaml) | Blueprint for hosting the API (e.g. Render). Frontend is deployed separately (Pages). |

---

## Prerequisites

- **Node.js 18+** and npm (`frontend`).
- **Python 3.10+** for the backend. JobSpy-heavy paths are tested around **3.11** (`start.sh` uses conda `python=3.11`).
- **`./start.sh` requires conda** ([Miniconda](https://docs.conda.io/en/latest/miniconda.html)). For venv-only workflows, follow [Backend](#backend-fastapi) below.

---

## Quick start (local)

From the repo root:

```bash
./start.sh
```

This:

1. Creates or reuses conda env **`job-resume-backend`** (override with `JOB_RESUME_BACKEND_CONDA_ENV`).
2. Installs `requirements.txt` + [`requirements-jobspy.txt`](backend-ai/requirements-jobspy.txt), starts **uvicorn** at `http://127.0.0.1:8000`.
3. Starts **`npm run dev`** in [`frontend`](frontend) at `http://localhost:3000` (copies `frontend/.env.example` → `.env.local` if missing).

API docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

## Backend (FastAPI)

**Manual setup (venv, no conda):**

```bash
cd backend-ai
python3.11 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install --no-deps -r requirements-jobspy.txt
alembic upgrade head
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Copy and edit **`backend-ai/.env`** from **[`backend-ai/.env.example`](backend-ai/.env.example)**.

**Migrations:** With `RUN_MIGRATIONS_ON_STARTUP=true` (default), the app runs Alembic on startup—fine for a single worker. For **multiple web workers**, set it to `false` and run `alembic upgrade head` once per deploy.

**Job scheduler:** `ENABLE_JOB_SCHEDULER` controls APScheduler in the web process—use **`false`** unless exactly one responsible process runs schedules.

Details on Indeed/ZipRecruiter opt-ins, proxies, Firecrawl, tailoring, mail, and CORS live in **`backend-ai/.env.example`** and **`app/core/config.py`**.

---

## Frontend (Next.js)

```bash
cd frontend
cp .env.example .env.local   # if you do not use start.sh
npm install
npm run dev
```

App: [http://localhost:3000](http://localhost:3000)

Set the API origin in **`frontend/.env.local`**. Prefer **`NEXT_PUBLIC_API_BASE`**; **`NEXT_PUBLIC_API_URL`** is a fallback ([`.env.example`](frontend/.env.example)).

**Production build** (matches static GitHub Pages flow):

```bash
cd frontend && npm run build
```

---

## Configuration

| Concern | Where to configure |
|---------|---------------------|
| API secrets, DB, JWT, CORS, job scraping, tailoring, mail, reset links | [`backend-ai/.env.example`](backend-ai/.env.example) |
| Browser API base URL | [`frontend/.env.example`](frontend/.env.example) → `.env.local` |
| Static deploy + **`PUBLIC_API_BASE_URL`** | [`.github/workflows/deploy-pages.yml`](.github/workflows/deploy-pages.yml) |

**Production API (minimum sanity):**

- `APP_ENV=production`
- Strong `JWT_SECRET` (never the dev placeholder)
- Valid `DATABASE_URL`
- **`FRONTEND_BASE_URL`** or **`APP_PUBLIC_ORIGIN`** for password-reset emails (HTTPS site origin, no path)
- Optional: `MAIL_TRANSPORT`, SMTP fields when you want real reset mail (default **`noop`** is safe)

---

## API overview

High-level grouping; see OpenAPI **`/docs`** for exact schemas.

**Public / health**

- `GET /api/health` — liveness-style check.

**Auth**

- `POST /api/auth/register`, `POST /api/auth/login`, `GET /api/auth/me`
- `POST /api/auth/change-password` (Bearer)
- `POST /api/auth/forgot-password`, `POST /api/auth/reset-password`

**Profile**

- `GET /api/profile`, `PATCH /api/profile`, `PUT /api/profile/resume`, `POST /api/profile/resume-upload`

**Resume tailoring**

- `POST /api/resume/tailor` — `TAILORING_PROVIDER` `stub` | `llm` (OpenRouter env when `llm`)

**Parsing / matching**

- `POST /api/parse`, `POST /api/match`, `POST /api/match/v2`

**Jobs aggregate (authenticated)**

- Search profiles CRUD under `/api/jobs/searches`, runs under `/api/jobs/runs`, results CSV, **`/api/jobs/board`** POST/GET/PATCH/**DELETE**.

**Dashboard**

- `GET /api/dashboard/summary`

**Other**

- `POST /api/jobs/import-preview` — URL scrape preview for wizard flows.

---

## Testing

**Backend** (from `backend-ai/` with deps installed):

```bash
pytest
```

**Frontend:**

```bash
cd frontend && npm test
npm run lint
```

---

## Deployment

Typical split:

1. **Frontend:** GitHub Actions workflow builds **static** Next.js and publishes to **`gh-pages`**. Set repository variable **`PUBLIC_API_BASE_URL`** to your HTTPS API origin (see workflow file).
2. **Backend:** Host FastAPI separately (example blueprint: **[`render.yaml`](render.yaml)**). Paste the deployed API URL into **`PUBLIC_API_BASE_URL`** so the Pages build bundles the correct `NEXT_PUBLIC_API_BASE`.

Ensure API **CORS** allows your Pages origin (`CORS_ORIGINS` and/or existing GitHub Pages regex in the backend). Configure **`FRONTEND_BASE_URL`** on the API for reset-email links.

---

## Troubleshooting

- **JobSpy / Indeed / ZipRecruiter** often return HTTP 403 from consumer IPs—the backend disables some sources by default. See comments in **`backend-ai/.env.example`** and optional **`JOBSPY_PROXY`**.
- **Python 3.9:** JobSpy stack may fail to import or install; prefer **3.10+**, ideally **3.11** per `start.sh`.
- **`next dev` ENOENT routes-manifest:** `start.sh` removes an incomplete **`frontend/.next`** when needed—if you hit this manually, **`rm -rf frontend/.next`** and run **`npm run dev`** again.

If something still fails after env and versions are correct, check **`/api/health`** and backend logs (`LOG_LEVEL`).
