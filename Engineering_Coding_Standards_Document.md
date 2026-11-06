# Engineering Coding Standards

**Project:** ReviewLens AI (repository: Group3Project) · **Story:** S1-001 · **Rules:** S1-BR-004, S1-BR-007, S1-BR-011

## Overview

This document sets the coding standards for ReviewLens AI. Every team member and every AI coding tool must follow it when writing or changing code, tests, or configuration. AI-generated code is treated as team-written code and must meet the same standards and Definition of Done.

**Stack:** React + TypeScript + Tailwind CSS (Vite) · FastAPI (Python 3.12) · MySQL (SQLAlchemy + Alembic) · Firebase Authentication · GitHub Actions CI.

**Non-negotiable rules (read these first):**

1. **Verify identity on the backend (S1-BR-004).** Every protected endpoint uses the shared auth dependency. Hiding a button or guarding a route in React is never enough.
2. **Every user-owned record has an owner and every query is owner-scoped (S1-BR-007).** Ownership comes only from the verified token, never from the client.
3. **No secrets in source control (S1-BR-011).** Keys, credentials, and `.env` files are never committed.

## 1. Repository and Folder Organization

Keep files in their designated locations.

```text
Group3Project/
├── frontend/                       React + TypeScript + Tailwind (Vite)
│   └── src/
│       ├── api/                    API client and request/response types
│       ├── auth/                   Firebase init, AuthProvider, ProtectedRoute
│       ├── components/
│       │   ├── ui/                 generic components (Button, Card, Alert)
│       │   └── reviewlens/         domain components (TargetCard, IngestionStatusBadge)
│       ├── hooks/                  shared React logic
│       ├── pages/                  route-level screens
│       ├── types/                  shared TypeScript types
│       └── lib/                    helpers, config, errorMessages.ts
├── backend/                        FastAPI (Python)
│   ├── app/
│   │   ├── main.py                 app factory, router registration
│   │   ├── config.py               settings read from environment
│   │   ├── auth/                   Firebase token verification dependency
│   │   ├── routers/                targets, ingestions, reviews (HTTP layer only)
│   │   ├── services/               business logic: targets, ingestion, normalizer
│   │   ├── adapters/               external services behind interfaces
│   │   │                           (ReviewSourceClient + fake; later LLMClient)
│   │   ├── models/                 SQLAlchemy models
│   │   ├── schemas/                Pydantic request/response schemas
│   │   └── db/                     session and engine setup
│   ├── migrations/                 Alembic migrations
│   └── tests/                      pytest; fixtures/ holds recorded sample data
├── docs/                           context documents (S1-001 to S1-004), setup guide
├── ai-transcripts/                 AI-assisted development transcripts
├── .github/workflows/              CI configuration
├── docker-compose.yml              local MySQL
└── .gitignore
```

Layer rules:

- **Routers** parse requests, call a service, and return a schema. No business logic or SQL in routers.
- **Services** hold business rules and ownership checks.
- **Adapters** wrap external systems (review provider, Firebase, later Claude). Other code depends on the adapter interface, never on a vendor SDK or response format.
- **Source-specific review parsing lives only in the adapter and normalizer.** The rest of the code sees the canonical `Review`.
- **Frontend components** do not call `fetch` directly; they use `src/api/`.

## 2. Naming Conventions

**Frontend (TypeScript / React / Tailwind CSS)**

| Item | Convention | Example |
|---|---|---|
| React component files and components | PascalCase | `TargetCard.tsx` |
| Hooks | camelCase, `use` prefix | `useTargets.ts` |
| Utility, service, and API files | camelCase | `errorMessages.ts` |
| Variables and functions | camelCase | `sourceUrl` |
| Types and interfaces | PascalCase | `AnalysisTarget` |
| Constants | UPPER_SNAKE_CASE | `MAX_NAME_LENGTH` |
| Custom CSS classes (rare) | kebab-case | `target-card-title` |

Use Tailwind utility classes directly in components; avoid custom CSS unless a utility cannot express it.

**Backend (Python / FastAPI)**

| Item | Convention | Example |
|---|---|---|
| Files and modules | snake_case | `ingestion_service.py` |
| Variables and functions | snake_case | `owner_id` |
| Classes and models | PascalCase | `AnalysisTarget` |
| Constants | UPPER_SNAKE_CASE | `INGESTION_MAX_REVIEWS` |
| API paths | lowercase, plural nouns | `/api/targets/{target_id}/reviews` |

**Database:** tables and columns use snake_case; tables are plural (`analysis_targets`, `reviews`); foreign keys are `<entity>_id` (`target_id`, `owner_id`).

## 3. Formatting and Linting Expectations

**Frontend**

- TypeScript strict mode is on. Do not use `any`; declare specific types. Use `unknown` and narrow it if the type is truly unknown.
- ESLint and Prettier are required. Format: 2-space indentation, single quotes, semicolons.
- `npm run lint`, `npm run format:check`, and `npm run build` must pass before opening a pull request.

**Backend**

- Ruff is used for both linting and formatting. Follow PEP 8.
- Add type hints to all function arguments and return types, for example `def create_target(data: TargetCreate, owner_id: str) -> AnalysisTarget:`.
- `ruff check .` and `ruff format --check .` must pass before opening a pull request.

**Both:** formatting is enforced by tooling and CI, not by editor preferences. Do not mix formatting-only changes into feature pull requests.

## 4. Authentication, Ownership, and Security (S1-BR-004, S1-BR-007)

These rules apply to every route, service, query, and test.

**Authentication (S1-BR-004)**

- Every protected route depends on the shared `get_current_user` dependency, which verifies the Firebase ID token and returns the trusted user identity. A missing or invalid token returns `401`.
- Do not write a protected route without this dependency. Do not re-implement token parsing in individual routes.
- Never read the user's identity from a request body, query string, or header other than the verified token.

**Ownership (S1-BR-007)**

- Every user-owned record (AnalysisTarget, and through it IngestionRun and Review) is stored with an owner and created with the owner taken from the verified token.
- Every query and mutation on user-owned data is scoped by owner, for example `WHERE id = :id AND owner_id = :user_id`. Never fetch by ID alone and check ownership afterwards in the browser.
- Child resources (ingestion runs, reviews) are authorized by loading the parent target as the owner first, before doing any work.
- If a target does not exist or belongs to someone else, return the same `404` response so existence is not revealed.
- Ignore any `user_id` or `owner_id` sent by the client.
- Frontend route guards and hidden controls are UX only. The backend is the authority.
- Every new user-owned endpoint ships with a cross-user test (see section 10).

## 5. Error-Handling Conventions

**Backend**

- `raise HTTPException` (or a project exception handled globally) for client errors. Use these statuses consistently:

| Status | Use |
|---|---|
| `401` | Missing or invalid authentication |
| `404` | Resource not found or not owned by the caller |
| `422` | Validation failure, with field details |
| `502` / `503` / `504` | Review provider unavailable or timing out |
| `500` | Unexpected failure |

- Never return raw database errors, provider error text, stack traces, or secrets to the client. Log the detail server-side and return a safe message.
- Ingestion failures record a failure category on the run (`invalid_source`, `provider_timeout`, `provider_quota`, `provider_unavailable`, `unexpected`). Quota, timeout, and unreachable service must stay distinct.
- A failed ingestion must never delete previously valid reviews or create fabricated ones.

**Frontend**

- Wrap external API calls in `try/catch` inside `src/api/`; pages do not build error strings.
- Map backend error codes to user-facing messages in one place (`src/lib/errorMessages.ts`).
- Show errors the way the UI/UX Standards document specifies: inline field errors for validation, inline alerts for section results, a full-page state for "not available". Never show raw errors, status codes, or provider or Firebase messages to users.

## 6. API and Service Response Conventions

- All endpoints return JSON defined by Pydantic schemas. No endpoint returns ad hoc dictionaries.
- Success responses: `200` for reads, `201` for creates, with the created resource in the body.
- Error responses use one shape:

```json
{
  "code": "validation_error",
  "message": "Enter a name for the business or product you want to analyze.",
  "fieldErrors": { "name": "Enter a name..." }
}
```

- `fieldErrors` is present only for validation failures, keyed by field name.
- Requests never include `user_id` or `owner_id`.
- Validation happens on the backend even if the frontend also validates (Pydantic schemas plus service-level checks).
- Review data returned to the client contains only what the UI needs; never return another user's data or internal fields.

## 7. Logging Expectations

- Do not use `print()` in application code. Use Python's `logging` module.
- **Format:** `[TIMESTAMP] [LEVEL] [MODULE]: Message`
- **Levels:**
  - `INFO`: normal events (for example, "Ingestion started for target 42").
  - `WARNING`: non-fatal issues (for example, "Provider slow, retrying request").
  - `ERROR`: failures (for example, "Database connection failed", "Ingestion failed: provider_quota").
- Include context that helps diagnosis: target ID, ingestion run ID, and an internal user identifier.
- **Security rule:** never log passwords, Firebase ID tokens, API keys, service-account contents, or full review text in bulk. Do not log secrets even at `DEBUG`.
- Frontend: no `console.log` of tokens or user data in committed code.

## 8. Secrets and Configuration (S1-BR-011)

- Never commit secrets: API keys, Firebase Admin credentials, database passwords, or provider keys.
- Configuration comes from environment variables, read in `backend/app/config.py` and `frontend/src/lib/config.ts`. No environment-specific value is hard-coded in source.
- Commit `.env.example` files with variable **names only**. Real values live in untracked `.env` files or CI secrets.
- `.gitignore` excludes `.env`, `.env.*` (except `.env.example`), `secrets/`, and service-account JSON files.
- The Firebase Admin credential and the review-provider API key are server-side only. Never place them in `frontend/`, in a `VITE_` variable, or in a browser network request. Only the Firebase web config is allowed in frontend variables.
- If a secret is committed by accident, rotate it first, then remove it from the repository.
- The backend fails at startup with a clear message when a required variable is missing.
- Tests never use real credentials.

## 9. Expectations for Adding Dependencies

- Do not add a library if the feature can be built simply with what the project already uses.
- **Frontend:** use `npm install <package>`, commit `package-lock.json`, and discuss large UI libraries with the team first.
- **Backend:** pin the dependency in `requirements.txt` (or `pyproject.toml`) and commit the change.
- Every new dependency is mentioned in the pull request with the reason it is needed.
- Verify that a package or API suggested by an AI tool actually exists and is actively maintained before installing it. Do not install packages from unfamiliar names without checking.
- Every new environment variable is added to the matching `.env.example` in the same pull request.

## 10. Expectations for Testing New or Changed Behavior

Every feature or fix includes at least one automated test update. CI must pass before merge.

**Backend (pytest)**

- Test observable behavior: expected result, validation failure, error cases, and boundaries.
- **Ownership:** every endpoint that touches user-owned data has a cross-user test (User B cannot read, modify, or ingest into User A's data) and an unauthenticated test (`401`, no data in the response).
- **Validation:** test both accepted and rejected input, and confirm invalid input is not persisted.
- **Persistence:** verify created data can be read back with the correct owner.
- **Ingestion:** use deterministic recorded fixtures in `tests/fixtures/`. Cover a valid review, missing text, missing or invalid rating, and absent optional metadata. Provider timeout, quota, and failure must produce distinct, non-fabricating outcomes.
- **No live services in tests.** Mock or fake Firebase token verification, the review provider, and (later) Claude. Tests must not need internet access or real credentials.

**Frontend (Vitest + React Testing Library)**

- Test critical helpers, hooks, and shared components (normal, error, and disabled states).
- Test that error messages map to user-friendly text and that raw errors are not rendered.

**Pull request rules**

- Every pull request runs lint, build, and tests in CI. A failing required check blocks the merge; no direct pushes to the protected branch.
- Adding or changing an API route or the database schema requires tests and, for schema changes, an Alembic migration. Otherwise the PR is blocked.
- The PR description includes a **Test Evidence** section naming the tests used to verify the change.
- Note significant assumptions or limitations in the PR or in `docs/`.

## 11. AI-Assisted Development

- AI tools receive this document and the other context documents in `docs/` as input.
- AI-generated code is reviewed, tested, and held to these standards before merge. The author remains responsible for understanding and securing it.
- Never paste secrets, tokens, or credential files into an AI tool.
- Keep AI session transcripts in `ai-transcripts/`.
