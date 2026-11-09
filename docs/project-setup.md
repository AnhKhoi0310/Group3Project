# Project Structure and Local Development Workflow

For all team members and AI coding tools working on ReviewLens. Story S1-005. Rule: S1-BR-011.

The root `README.md` is the quick start. This document explains how the repository is laid out, where configuration comes from, and how the checks and CI fit together. If the two disagree, fix both in the same pull request.

## 1. Repository layout

```text
Group3Project/
├── frontend/                 React + TypeScript + Tailwind (Vite)
│   └── src/
│       ├── api/              API client (attaches the Firebase ID token, parses errors)
│       ├── auth/             Firebase client, AuthContext, RequireAuth route guard
│       ├── components/       shared UI: Button, TextField, ErrorMessage, LoadingIndicator
│       ├── config/           env.ts reads VITE_ variables in one place
│       ├── pages/            route-level screens (LoginPage, TargetsPage)
│       └── test/             test setup and fake auth client
├── backend/                  FastAPI on Python 3.12
│   ├── app/
│   │   ├── main.py           app, CORS, error handler, router registration, /api/health
│   │   ├── config.py         settings read from the environment (fails fast if missing)
│   │   ├── auth.py           get_current_user and token verifier dependencies
│   │   ├── adapters/         external services behind interfaces (identity.py for Firebase)
│   │   ├── repositories/     database access (users.py)
│   │   ├── routers/          HTTP layer only (auth.py)
│   │   ├── models.py         SQLAlchemy models
│   │   ├── db.py             engine, session, Base
│   │   └── errors.py         ApiError and its handler
│   ├── migrations/           Alembic migrations (versions/)
│   ├── tests/                pytest
│   ├── Dockerfile
│   ├── requirements.txt      runtime dependencies, pinned
│   └── requirements-dev.txt  adds pytest and ruff
├── docs/                     team standards for developers and AI tools
├── ai-transcripts/           AI-assisted development transcripts
├── .github/workflows/        ci.yml (pull request checks)
├── docker-compose.yml        local MySQL, backend, and frontend
├── .env.example              root template: MySQL passwords and host port
└── README.md                 quick start
```

### Responsibilities

| Area | Responsibility |
|---|---|
| `frontend/` | User interface only. Calls the backend through `src/api/`. Holds no secrets. |
| `backend/` | Token verification, ownership, validation, business rules, persistence, and (later) review-provider calls. |
| MySQL 8.4 | Persistent storage. Schema changes go through Alembic migrations only. |
| Firebase Authentication | Managed identity. The backend verifies its tokens and maps the Firebase `uid` to a `users` row. |

### Layout is still growing

The folder layout in `docs/coding-standards.md` is the target. Today's repository is smaller. Folders such as `services/`, `schemas/`, `models/`, `db/`, `components/ui/`, `components/reviewlens/`, `hooks/`, `types/`, and `lib/` appear when a story first needs them. Do not create empty folders ahead of time. When you add code to one of these areas, follow `docs/coding-standards.md` rather than extending the flat files.

## 2. Configuration and secrets (S1-BR-011)

Three templates are committed. Real values live only in untracked `.env` files.

| Template | Copy to | Used by |
|---|---|---|
| `.env.example` | `.env` | Docker Compose: MySQL passwords and `MYSQL_HOST_PORT` |
| `backend/.env.example` | `backend/.env` | Backend settings |
| `frontend/.env.example` | `frontend/.env` | Frontend (public values only) |

### Where each value comes from

| Variable | Secret? | Where to get it |
|---|---|---|
| `MYSQL_ROOT_PASSWORD`, `MYSQL_PASSWORD` | Yes | Choose your own for local Docker. Avoid `@ : /` in them. |
| `DATABASE_URL` | Yes | Local MySQL URL. Docker Compose builds its own, so this is only for running without Docker. |
| `FIREBASE_PROJECT_ID` | No | Firebase console > Project settings |
| `FIREBASE_CREDENTIALS_PATH` | Points to a secret | Path to the Admin key, relative to `backend/`. Default `secrets/firebase-admin.json`. |
| `REVIEW_PROVIDER_API_KEY` | Yes | Account with the team's chosen review-data provider |
| `CORS_ALLOWED_ORIGINS` | No | Optional. Defaults to `http://localhost:5173`. |
| `INGESTION_MAX_REVIEWS` | No | Optional. Positive whole number. Defaults to 50. |
| `VITE_API_BASE_URL` | No | Backend URL, normally `http://localhost:8000` |
| `VITE_FIREBASE_*` (API key, auth domain, project ID, app ID) | No, public by Firebase design | Firebase console > Project settings > Your apps |

### Getting the shared credentials

> **Team: fill this in before sharing the repo.** Name who holds the Firebase Admin key, the Firebase web config, and the review-provider key, and how teammates receive them (for example a password manager or a private direct message). Never send them through git, pull requests, issues, public channels, or an AI tool.

### Rules

- Never commit `.env` files, anything in `secrets/`, or service-account JSON. `.gitignore` excludes them. Check `git status` before committing.
- Never put a secret in a `VITE_` variable. Everything with that prefix is bundled into browser code.
- Do not hard-code environment-specific values. Backend code reads settings through `app/config.py`. Frontend code reads them through `src/config/env.ts`.
- Adding a variable means adding its name to the matching `.env.example` in the same pull request.
- The backend refuses to start when a required variable is missing and names it, without printing its value. Check without starting the server by running `python -m app.config` from `backend/`.
- If a secret is committed by accident, rotate it first, then remove it from the repository.

## 3. Running the application locally

### With Docker (recommended)

1. Install Python 3.12, Node 22 (20.19 or later also works), and Docker Desktop.
2. Create the three `.env` files from their templates and fill in the values.
3. Place the Firebase Admin key at `backend/secrets/firebase-admin.json`. The backend will not start without it.
4. From the repository root:

```bash
docker compose up --build
```

Compose starts MySQL, waits for its health check, runs `alembic upgrade head`, then starts the backend with reload. The frontend also runs with hot reload.

| Service | Address |
|---|---|
| Frontend | http://localhost:5173 |
| Backend health check | http://localhost:8000/api/health (returns `{"status": "ok"}`) |
| MySQL | `localhost:3306`, or `MYSQL_HOST_PORT` if set |

If another MySQL already uses port 3306, set `MYSQL_HOST_PORT` in the root `.env`.

### Without Docker

Backend, from `backend/`, with a MySQL 8 reachable at `DATABASE_URL` (for example `docker compose up db`):

```bash
python -m venv .venv
.venv\Scripts\activate          # macOS/Linux: source .venv/bin/activate
pip install -r requirements-dev.txt
alembic upgrade head
uvicorn app.main:app --reload
```

Frontend, from `frontend/`:

```bash
npm ci
npm run dev
```

### Database migrations

- Schema changes require an Alembic migration. Generate one with `alembic revision --autogenerate -m "describe the change"` and read it before committing.
- Never edit the database by hand and never edit a migration that has been merged. Add a new one.

### Resetting local data

`docker compose down -v` removes the MySQL volume and all local data. Run `docker compose up --build` afterwards to recreate it.

## 4. Quality checks

These are the same commands CI runs. Run them before opening a pull request.

| Check | Backend (`backend/`) | Frontend (`frontend/`) |
|---|---|---|
| Lint | `ruff check .` | `npm run lint` |
| Format check | `ruff format --check .` | `npm run format:check` |
| Apply formatting | `ruff format .` | `npm run format` |
| Build | `python -m compileall -q app` | `npm run build` (type-checks, then builds) |
| Tests | `pytest` | `npm test` |

### Database tests

Backend tests that touch MySQL need a separate database. Without `TEST_DATABASE_URL` they are skipped locally. CI always runs them and fails if the variable is missing. The database name must contain `test`, because the tests erase its data and refuse to run against anything else.

```bash
TEST_DATABASE_URL=mysql+pymysql://user:password@127.0.0.1:3306/reviewlens_test pytest
```

### Test rules

- Tests never call live Firebase, a live review provider, or an LLM. Use the fake token verifier (backend) and the fake auth client (`src/test/fakeAuth.ts`, frontend).
- Every feature or fix includes at least one automated test.
- Frontend formatting uses `endOfLine: "auto"` in `frontend/.prettierrc.json`, so Windows, macOS, and Linux line endings do not fail the format check.

## 5. Continuous integration

`.github/workflows/ci.yml` runs on every pull request and on pushes to `main`. It has two jobs.

| Job | Steps |
|---|---|
| Backend checks | Install dependencies, `ruff check`, `ruff format --check`, build (`compileall`), `pytest` against a MySQL 8.4 service container |
| Frontend checks | `npm ci`, lint, format check, build, tests |

The credentials in the CI workflow belong to a throwaway database container and are not real secrets. No real secrets are used in CI.

Failing required checks must block merge to `main`. This is enforced in the GitHub repository's branch protection settings, not by the workflow file alone. See S1-007.

`.github/workflows/import-sprint-issues.yml` is a manually triggered helper that creates issues from `Sprint1Issues.csv`. It is not part of the quality gate.

## 6. Working on a story

1. Branch from `main`, named for the story (for example `feature/S1-015-create-target`).
2. Give your AI tool the context listed in `docs/ai-assisted-development.md`.
3. Run the quality checks in section 4 locally.
4. Open a pull request that references the story ID and includes a **Test Evidence** section.
5. Commit your AI transcript to `ai-transcripts/` in the same pull request or the same working day.
6. Merge only after CI passes and a teammate approves.

## 7. Verifying this setup (S1-005 acceptance)

The story is complete only when someone other than the author can run the application from the README. Record the result in the pull request.

- [ ] Fresh clone on a machine that has never run the project
- [ ] Three `.env` files created and Firebase key placed
- [ ] `docker compose up --build` succeeds
- [ ] Frontend loads at http://localhost:5173
- [ ] http://localhost:8000/api/health returns `{"status": "ok"}`
- [ ] Non-Docker path starts both backend and frontend
- [ ] `ruff check .`, `ruff format --check .`, `pytest`, `npm run lint`, `npm run format:check`, `npm run build`, and `npm test` all pass
- [ ] Removing a required variable from `backend/.env` makes the backend stop with a message naming it
- [ ] `git ls-files` shows no `.env` file, `secrets/` content, or service-account JSON
