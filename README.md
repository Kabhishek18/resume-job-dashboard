# Resume Job Dashboard (MVP scaffold)

Monorepo layout:

- **`backend-ai/`** — FastAPI app: `/api/health`, `/api/parse`, `/api/match`, auth/profile, URL import preview, tailoring (stub vs `llm` placeholder). Alembic migrations. Python 3.9+.
- **`frontend/`** — Next.js (App Router) + Tailwind + shadcn/ui. Resume wizard (match + tailor) posts to the API.

## Prerequisites

- Node.js 18+ (npm).
- Python 3.9+ with `pip`.

## Backend (FastAPI)

```bash
cd backend-ai
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

The app runs **Alembic migrations** on startup as well; `alembic upgrade head` keeps the DB current if you run workers without the FastAPI lifespan.

Open interactive docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

## Frontend (Next.js)

```bash
cd frontend
cp .env.example .env.local
npm install
npm run dev
```

App: [http://localhost:3000](http://localhost:3000). Use **Resume** to run a match against the backend.

Set `NEXT_PUBLIC_API_URL` in `frontend/.env.local` if the API is not at `http://127.0.0.1:8000`.

## API contract (MVP)

- **Auth/profile:** register/login; `GET /api/profile`; `PUT /api/profile/resume` (Bearer token).
- **Match:** `POST /api/match` with `raw_resume_text` and `job` (`raw_text`, optional `title`, `company`, `url`).
- **Job import:** `POST /api/jobs/import-preview` with `{ url }` — generic page extraction; fallback when empty.
- **Tailor:** `POST /api/resume/tailor` — request includes `resume_text`, `job`, `include_cover_letter`, optional `match_snapshot`. Default `provider_mode` is stub; `TAILORING_PROVIDER=llm` responds with 501 until wired.
