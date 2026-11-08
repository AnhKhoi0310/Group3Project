# ReviewLens AI

A multi-user web app for ingesting a business's public reviews and, from Sprint 2, asking questions answered only from those reviews. CS 490 capstone.

- `frontend/`: React, TypeScript, Vite, Tailwind
- `backend/`: FastAPI on Python 3.12
- `docker-compose.yml`: local MySQL 8, backend, and frontend
- `docs/`: team standards for developers and AI coding tools

## Requirements

Python 3.12, Node 22 (20.19 or later also works), and Docker Desktop.

## Configure

Copy each template and fill in your values. Each file explains its own variables.

```
cp .env.example .env
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
```

Put the Firebase Admin key at `backend/secrets/firebase-admin.json`. Never commit `.env` files or anything in `secrets/`.

The app refuses to start if required configuration is missing, and names what is missing. To check backend configuration on its own, run `python -m app.config` from `backend/`.

## Run with Docker

```
docker compose up --build
```

Frontend: http://localhost:5173. Backend health check: http://localhost:8000/api/health.

## Run without Docker

Backend, from `backend/`:

```
python -m venv .venv
.venv\Scripts\activate        # macOS/Linux: source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload
```

Frontend, from `frontend/`:

```
npm ci
npm run dev
```

## Checks

These are the same checks CI runs on every pull request.

| | Backend (`backend/`) | Frontend (`frontend/`) |
|---|---|---|
| Lint | `ruff check .` | `npm run lint` |
| Format check | `ruff format --check .` | `npm run format:check` |
| Apply formatting | `ruff format .` | `npm run format` |
| Build | `python -m compileall -q app` | `npm run build` |
| All tests | `pytest` | `npm test` |
| One test | `pytest tests/test_config.py::test_settings_repr_masks_secrets` | `npx vitest run src/Root.test.tsx -t "valid"` |

## Pull requests

Work on a feature branch and reference the story ID (for example, S1-015). Every PR needs a short Test Evidence section. Failing checks block merge to `main`.
