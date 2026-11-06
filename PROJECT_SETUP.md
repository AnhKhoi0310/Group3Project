# ReviewLens AI – Project Structure & Local Development Workflow (S1-005)

**Story:** S1-005 · **Rule:** S1-BR-011 · **Outcome:** a teammate can clone the repo, follow this page, and run the Sprint 1 app locally without asking anyone for help.

The repo is a **monorepo** with a React frontend, a FastAPI backend, and MySQL running in Docker. Commands below assume the stack in the Tech Stack & Architecture Baseline; adjust names if the team's actual tooling differs, and keep this page in sync with the repo.

## 1. Repository Layout

```
reviewlens/
├─ frontend/                  React + TypeScript + Tailwind (Vite)
│  ├─ src/
│  │  ├─ api/                 API client, request/response types
│  │  ├─ components/ui/       generic components (Button, Card, Alert...)
│  │  ├─ components/reviewlens/ domain components (TargetCard...)
│  │  ├─ pages/               route-level screens
│  │  ├─ auth/                Firebase init, AuthProvider, ProtectedRoute
│  │  └─ lib/                 helpers, errorMessages.ts, config
│  ├─ .env.example
│  └─ package.json
├─ backend/                   FastAPI (Python 3.12)
│  ├─ app/
│  │  ├─ main.py              app factory, router registration
│  │  ├─ config.py            settings loaded from environment
│  │  ├─ auth/                Firebase token verification dependency
│  │  ├─ routers/             targets, ingestions, reviews
│  │  ├─ services/            target, ingestion, normalizer
│  │  ├─ adapters/            ReviewSourceClient (provider + fake)
│  │  ├─ models/              SQLAlchemy models
│  │  └─ schemas/             Pydantic request/response schemas
│  ├─ migrations/             Alembic migrations
│  ├─ tests/                  pytest (unit, with fixtures/)
│  ├─ .env.example
│  └─ pyproject.toml          (or requirements.txt + requirements-dev.txt)
├─ docker-compose.yml         local MySQL
├─ docs/                      context documents (S1-001 to S1-004), this page
├─ ai-transcripts/            AI-assisted development transcripts
├─ .github/workflows/         CI (S1-007)
├─ .gitignore                 excludes .env files and credential files
└─ README.md                  links to this setup guide
```

## 2. Responsibilities

| Area | Location | Owns | Must not |
|---|---|---|---|
| Frontend | `frontend/` | Screens, Firebase sign-in, calling the backend, showing states and errors | Hold provider API keys, make ownership decisions, call the review provider directly |
| Backend | `backend/` | Token verification, ownership enforcement, validation, ingestion, persistence | Trust client-supplied user IDs, return stack traces |
| Persistent storage | MySQL via `docker-compose.yml`; connection in `DATABASE_URL`; schema in `backend/migrations/` | All user-owned data | Be edited by hand; schema changes go through migrations |
| External services | Firebase (auth), review provider (ingestion) | Identity, review data | Be called from tests |

## 3. Prerequisites

| Tool | Version | Check |
|---|---|---|
| Git | any recent | `git --version` |
| Node.js | 20 LTS or newer | `node --version` |
| Python | 3.12 | `python --version` |
| Docker Desktop (with Compose) | any recent | `docker compose version` |

You also need access to the team's Firebase project and (for live ingestion) the review provider key. Ask the team lead; never paste either into chat or commits.

## 4. First-Time Setup

### 4.1 Clone

```bash
git clone <repo-url> reviewlens
cd reviewlens
```

### 4.2 Start the database

```bash
docker compose up -d db
docker compose ps          # db should show "healthy" / "running"
```

### 4.3 Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env               # Windows: copy .env.example .env
# edit .env with your values (see section 5)
alembic upgrade head               # create the schema
```

### 4.4 Frontend

```bash
cd frontend
npm ci
cp .env.example .env               # Windows: copy .env.example .env
# edit .env with the Firebase web config (see section 5)
```

## 5. Configuration (S1-BR-011)

No environment-specific value is hard-coded in source. Everything below comes from environment variables read in `backend/app/config.py` and `frontend/src/lib/config.ts`. Committed `.env.example` files list **names only**; real values live in untracked `.env` files.

### Backend (`backend/.env`)

| Variable | Purpose | Example (non-secret placeholder) |
|---|---|---|
| `DATABASE_URL` | MySQL connection | `mysql+pymysql://reviewlens:reviewlens@localhost:3306/reviewlens` |
| `FIREBASE_PROJECT_ID` | Token audience check | `your-firebase-project-id` |
| `FIREBASE_ADMIN_CREDENTIALS` | Path to the service-account JSON (kept outside git) | `./secrets/firebase-admin.json` |
| `REVIEW_PROVIDER_API_KEY` | Review-data provider key (server-side only) | `replace-me` |
| `INGESTION_MAX_REVIEWS` | Cap on reviews per run | `50` |
| `ALLOWED_ORIGINS` | CORS origins | `http://localhost:5173` |

### Frontend (`frontend/.env`)

These are bundled into browser code, so they must be public-by-design values only.

| Variable | Purpose |
|---|---|
| `VITE_API_BASE_URL` | Backend base URL, e.g. `http://localhost:8000` |
| `VITE_FIREBASE_API_KEY`, `VITE_FIREBASE_AUTH_DOMAIN`, `VITE_FIREBASE_PROJECT_ID`, `VITE_FIREBASE_APP_ID` | Firebase web config (designed by Firebase to be public) |

### Secret-handling rules

- `.gitignore` must exclude `.env`, `.env.*` (except `.env.example`), `secrets/`, and any `*-admin*.json`.
- Never put the Firebase Admin credential or the provider API key in `frontend/`, in a `VITE_` variable, or in a browser network request.
- If a secret is committed by accident, treat it as leaked: rotate it first, then remove it from the repo.
- The backend fails at startup with a clear message naming any missing required variable.

## 6. Run the App

Use two terminals (database already running from section 4.2).

```bash
# Terminal 1 – backend (from backend/, venv active)
uvicorn app.main:app --reload --port 8000

# Terminal 2 – frontend (from frontend/)
npm run dev
```

| Service | URL |
|---|---|
| Frontend | http://localhost:5173 |
| Backend API | http://localhost:8000 |
| API docs (FastAPI) | http://localhost:8000/docs |
| Health check | http://localhost:8000/health |

### Verify it works

1. `http://localhost:8000/health` returns a success response.
2. Opening `http://localhost:5173/targets` while signed out redirects to `/login`.
3. Signing in lands on the targets list.
4. `curl http://localhost:8000/api/targets` with no token returns `401` and no data.

## 7. Everyday Commands

| Task | Directory | Command |
|---|---|---|
| Backend tests | `backend/` | `pytest` |
| Backend lint + format check | `backend/` | `ruff check . && ruff format --check .` |
| Frontend tests | `frontend/` | `npm test` |
| Frontend lint | `frontend/` | `npm run lint` |
| Frontend format check | `frontend/` | `npm run format:check` |
| Frontend build | `frontend/` | `npm run build` |
| New migration | `backend/` | `alembic revision --autogenerate -m "describe change"` |
| Apply migrations | `backend/` | `alembic upgrade head` |
| Stop database | repo root | `docker compose down` |
| Reset database (deletes local data) | repo root | `docker compose down -v`, then section 4.2 and `alembic upgrade head` |

These match what CI runs, so a clean local run predicts a green pull request. Tests use fakes and fixtures, so they need no Firebase, provider key, or internet access.

## 8. Troubleshooting

| Symptom | Likely cause and fix |
|---|---|
| Backend exits at startup naming a variable | Missing value in `backend/.env`; compare with `.env.example` |
| `Can't connect to MySQL` | Database not running or still starting: `docker compose ps`, wait for healthy, retry |
| Port 3306, 8000, or 5173 already in use | Stop the other process or change the port in `.env` / compose file and keep `ALLOWED_ORIGINS` in sync |
| Browser shows a CORS error | `ALLOWED_ORIGINS` doesn't include the frontend URL |
| Sign-in works but every API call returns 401 | `FIREBASE_PROJECT_ID` or the admin credential path is wrong |
| Frontend blank or Firebase error on load | Missing or wrong `VITE_FIREBASE_*` values; restart `npm run dev` after editing `.env` |
| Tables missing | Migrations not applied: `alembic upgrade head` |

## 9. Conventions for Keeping This Repeatable

- Pin dependencies: commit `package-lock.json` and the Python lockfile or pinned requirements; install with `npm ci`.
- Every new environment variable is added to the matching `.env.example` and to section 5 in the same pull request.
- Every new setup step is added to this page in the same pull request.
- Do not depend on one person's machine: at least one teammate other than the author must run sections 4–6 from a fresh clone before this story is marked done.

## 10. Definition of Done for S1-005

- [ ] Frontend, backend, and database configuration are each identifiable in the repo layout
- [ ] A fresh clone follows section 4 and reaches a running app with no undocumented steps
- [ ] `docker compose up -d db` starts local MySQL and `alembic upgrade head` creates the schema
- [ ] Both `.env.example` files exist and list every required variable name with no real values
- [ ] No secret, credential file, or `.env` is tracked by git (`git ls-files` check)
- [ ] Required variables missing at startup produce a clear error
- [ ] A second teammate has verified the setup on their own machine
- [ ] The pull request includes a Test Evidence section (for example: backend `pytest` and frontend `npm test` both pass from a clean clone)
