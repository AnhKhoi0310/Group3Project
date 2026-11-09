# Engineering Coding Standards

For developers and AI coding tools changing ReviewLens. Story S1-001. Install and check commands are in the root `README.md`.

## Repository organization

```
backend/app/
  main.py          FastAPI app and startup
  config.py        All environment configuration
  routers/         HTTP only: parse the request, call a service, shape the response
  services/        Business logic: targets, ingestion, normalizer
  adapters/        External services: ReviewSourceClient, later LLMClient
  repositories/    All database access
  models/          SQLAlchemy models
backend/tests/
frontend/src/
  config/          Environment configuration
  pages/           One component per route
  components/      Reusable UI
  api/             All backend calls
```

Only `main.py` and `config.py` exist today. Add the other folders as stories need them, in these locations.

Dependencies point one way: routers → services → adapters and repositories. Routers don't touch the database. Source-specific parsing lives only in the adapter and normalizer.

## Naming

| Thing | Convention | Example |
|---|---|---|
| Python modules, functions, variables | `snake_case` | `fetch_reviews` |
| Python classes | `PascalCase` | `AnalysisTarget` |
| Database tables and columns | plural `snake_case` tables | `ingestion_runs.target_id` |
| API paths | `/api/` plus plural nouns | `/api/targets/{id}/reviews` |
| React components and their files | `PascalCase` | `TargetList.tsx` |
| TypeScript functions, variables | `camelCase` | `loadConfig` |
| Tests | beside source (frontend), `tests/test_*.py` (backend) | `env.test.ts` |

Use the domain terms User, AnalysisTarget, IngestionRun, and Review. Don't introduce synonyms.

## Formatting and linting

Ruff (backend) and ESLint with Prettier (frontend) are the only authorities, and CI enforces them. Don't hand-format against them or disable a rule without a comment explaining why.

## Error handling and API responses

Every API error uses one JSON shape:

```json
{ "code": "target_not_found", "message": "We couldn't find that target.", "fieldErrors": { "name": "Enter a name." } }
```

`fieldErrors` is optional. `message` must make sense to an ordinary user. Stack traces, database errors, and provider text never reach the client.

| Situation | Status |
|---|---|
| Created | 201 |
| Validation failure | 422 |
| Missing or invalid token | 401 |
| Not found, or owned by someone else | 404 (identical response) |

The frontend maps `code` to the categories validation, authentication, authorization, ingestion, and unexpected.

Ingestion failures record one `failure_category`: `invalid_source`, `provider_timeout`, `provider_quota`, `provider_unavailable`, or `unexpected`. Never merge timeout, quota, and unreachable into one case.

## Logging

Use Python's `logging` module on the backend, not `print`. Log technical detail on the server with the target ID or run ID. Never log tokens, API keys, database URLs, or full provider responses.

## Configuration

Read backend configuration only through `app.config`, and frontend configuration only through `src/config/env.ts`. A new variable must be added to the loader, its `.env.example`, and its tests in the same change.

## Adding dependencies

Pin exact Python versions in `requirements.txt` (runtime) or `requirements-dev.txt` (tooling). Commit `package-lock.json`. Before adding one, confirm the package exists and is maintained, and say why it's needed in the PR. We don't use MongoDB, vector databases, or job queues in Sprint 1.

## Testing

Each feature story adds or updates at least one automated test, including the failure path.

- Test observable behavior, not internals.

Today auth.py, db.py, errors.py, and models.py are single files beside main.py and config.py. Split models.py into a models/ package once it holds more than a few models. Add services/ and the other missing folders as stories need them, in these locations.
- CI never calls a live provider. Use the fake `ReviewSourceClient` and the committed fixture.
- Replace `get_current_user` in tests with fake User A and User B identities.
- Ownership tests need two users and must prove User B is denied and User A's data is unchanged.
- Persistence tests must read the data back.
