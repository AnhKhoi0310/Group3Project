# Data and Security Guardrails

**Project:** ReviewLens AI (repository: Group3Project) · **Story:** S1-003 · **Rules:** S1-BR-001 through S1-BR-011

This document is for every developer and every AI coding tool that touches ReviewLens. It explains who owns what, how identity is established, where authorization happens, how secrets are handled, and how cross-user isolation is tested.

**The one-sentence version:** ReviewLens is a multi-user application, so every user-owned query and mutation must be scoped to the authenticated owner on the backend, using an identity taken from a verified Firebase token and never from anything the client sends.

If a change you are making reads or writes user-owned data and you cannot point to where the owner is enforced, stop and fix that before continuing.

## 1. Rule Coverage Map

| Rule | Requirement | Where this document handles it |
|---|---|---|
| S1-BR-001 | Use a managed identity service | Section 2 |
| S1-BR-002 | No self-built password or credential system | Section 2 |
| S1-BR-003 | Authentication required for all protected functionality | Sections 3, 5 |
| S1-BR-004 | Backend verifies identity on protected requests | Sections 3, 5 |
| S1-BR-005 | Provider identity mapped to application user data | Section 3 |
| S1-BR-006 | After logout, the old session no longer grants access | Section 3.4 |
| S1-BR-007 | User-scoped records have an authenticated owner | Section 4 |
| S1-BR-008 | Cross-user read, write, update, ingestion denied | Sections 5, 6, 9 |
| S1-BR-009 | Authorization enforced on backend or persistence layer | Section 5 |
| S1-BR-010 | Client-supplied user or owner ID never trusted | Section 7 |
| S1-BR-011 | Secrets never in source control or browser code | Section 8 |

## 2. Identity Provider (S1-BR-001, S1-BR-002)

- **Selected provider: Firebase Authentication** (a managed identity service).
- **Firebase is responsible for:** registration, sign-in, credential storage, password hashing, password reset, session and token issuance, duplicate-email handling.
- **ReviewLens is responsible for:** verifying the Firebase ID token on every protected backend request, mapping the Firebase identity to a ReviewLens user, and enforcing ownership. Firebase does **not** do authorization; installing the SDK and hiding UI controls satisfies none of this.
- **We never build:** password storage, password hashing, a credential table, or a custom reset flow.

## 3. Authentication and Identity Mapping (S1-BR-003 to S1-BR-006)

### 3.1 How a request is authenticated

1. The browser signs in through the Firebase SDK and receives an ID token.
2. The frontend API client sends `Authorization: Bearer <ID token>` on every backend call.
3. The backend dependency `get_current_user` verifies the token with the Firebase Admin SDK (signature, expiry, audience/project) and extracts the stable Firebase `uid`.
4. Missing, malformed, or invalid tokens return `401` with no data.

```python
# backend/app/auth/dependencies.py (shape, not final code)
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    claims = token_verifier.verify(credentials.credentials)   # raises -> 401
    return user_service.get_or_create_by_firebase_uid(db, claims["uid"], claims.get("email"))
```

Every protected route must declare `user: User = Depends(get_current_user)`. A protected route without it is a defect.

### 3.2 Mapping provider identity to ownership (S1-BR-005)

| Concept | Value |
|---|---|
| Provider identity | Firebase `uid` (stable, unique per account) |
| Application user | Row in `users`, with `id` (internal primary key), `firebase_uid` (unique), `email`, `created_at` |
| Mapping | On the first authenticated request, `get_or_create_by_firebase_uid` creates the `users` row; later requests look it up |
| Ownership reference | `analysis_targets.owner_id` is a foreign key to `users.id` |

The internal `users.id` is what services and queries use as `owner_id`. The Firebase `uid` is only used at the boundary to find or create the user. The email is informational and is never used as the ownership key.

### 3.3 Frontend behavior (UX only)

- `ProtectedRoute` redirects unauthenticated visitors to `/login`, and the API client attaches a fresh token. These improve usability; they are **not** security controls (S1-BR-009).
- The frontend never sends a user ID or owner ID (Section 7).

### 3.4 Logout (S1-BR-006)

- The UI signs out through Firebase `signOut`, clears cached targets and reviews from client state, and redirects to `/login`.
- Firebase ID tokens stay valid until they expire (about one hour) unless revoked. To make logout cut off access on the backend as well, the team's chosen approach is: `POST /api/auth/logout` (authenticated) calls the Admin SDK `revoke_refresh_tokens(uid)`, and token verification uses `check_revoked=True`. **Confirm this approach as a team** (it adds a revocation lookup per request); if a different approach is chosen, document it here.
- Test evidence for S1-BR-006: a token captured before logout is rejected (`401`) after logout, and the UI no longer shows protected pages.

## 4. User-Scoped Entities (S1-BR-007)

| Entity | Owner relationship | How ownership is resolved |
|---|---|---|
| `User` | The account itself | `firebase_uid` mapped to `users.id` |
| `AnalysisTarget` | **Direct:** `owner_id` → `users.id` | Stored on the row, set from the verified user at creation |
| `IngestionRun` | **Transitive:** `target_id` → `analysis_targets` | Always reached through an owned target |
| `Review` | **Transitive:** `target_id` → `analysis_targets` (also `ingestion_run_id`) | Always reached through an owned target |
| Chat or Q&A data (Sprint 2) | Transitive through the target | Same rule; AI context must contain only the active owned target's reviews |

Rules:

- A user-scoped record without a resolvable owner must not exist. `owner_id` is `NOT NULL` with a foreign key.
- Ownership is transitive: reviews and ingestion data are accessible only through an `AnalysisTarget` owned by the authenticated user.
- Deleting a target cascades to its runs and reviews. Delete operations enforce the same ownership rules as reads.

## 5. Where Authorization Is Enforced (S1-BR-004, S1-BR-008, S1-BR-009)

| Layer | Role | Authoritative? |
|---|---|---|
| Frontend route guards, hidden buttons, filtered lists | Usability | **No** |
| FastAPI `get_current_user` dependency | Authentication: who is calling | Yes |
| **Service and repository layer** | **Authorization: does this user own this resource** | **Yes (primary)** |
| Database foreign keys and constraints | Integrity of ownership relationships | Yes (supporting) |

### 5.1 Rules for the backend

1. **Owner is a required parameter of every user-data function.** Repository and service functions take `owner_id` explicitly, so the code cannot compile a query that forgets it.
2. **Fetch by ID and owner together.**

```python
# Correct: ownership is part of the query
def get_target_for_owner(db: Session, target_id: int, owner_id: int) -> AnalysisTarget | None:
    return db.scalar(
        select(AnalysisTarget).where(
            AnalysisTarget.id == target_id,
            AnalysisTarget.owner_id == owner_id,
        )
    )
```

3. **Child resources are authorized through the parent first.** Before touching runs or reviews, load the target with `get_target_for_owner`. If it returns `None`, stop with `404`. Review queries join through the owned target.

```python
def list_reviews_for_owner(db: Session, target_id: int, owner_id: int) -> list[Review]:
    target = get_target_for_owner(db, target_id, owner_id)
    if target is None:
        raise NotFoundError()
    return db.scalars(select(Review).where(Review.target_id == target.id)).all()
```

4. **Authorize before doing work.** Ingestion checks target ownership before calling the review provider, creating a run, or writing anything.
5. **List endpoints filter in the query**, for example `WHERE owner_id = :user_id`. Never load everyone's rows and filter afterwards.
6. **Same response for "not found" and "not yours."** Both return `404` with the same body so a user cannot discover other users' resource IDs.
7. **Mutations and deletes** (update, delete, ingest, import) use the same owner-scoped lookup as reads.
8. **Background tasks** carry the `owner_id` and re-check ownership; they do not use ambient or global state.

## 6. Prohibited Data-Access Patterns

Do not write, and reject in review, any of the following.

| Prohibited pattern | Why it is wrong |
|---|---|
| `db.get(AnalysisTarget, target_id)` or `WHERE id = :id` alone, then returning the result | No ownership check: any user can read any target by ID |
| Reading `owner_id` or `user_id` from the request body, query string, path, or a custom header | Client-controlled value (Section 7) |
| Fetching all targets or reviews and filtering in Python or the browser | Leaks other users' data to the server process or client |
| Querying reviews by `target_id` without first verifying the target belongs to the caller | Cross-user review access |
| Starting ingestion, creating a run, or calling the provider before verifying target ownership | Cross-user ingestion and wasted quota |
| A protected route without `Depends(get_current_user)` | Unauthenticated access |
| Re-implementing token parsing inside a route | Inconsistent verification |
| Returning `403` for another user's resource and `404` for a missing one | Reveals that the resource exists |
| Admin, debug, or "internal" endpoints that return any user's data | Backdoor that bypasses isolation |
| Cache or global variables shared across users (module-level state holding user data) | Cross-user leakage |
| Raw SQL that omits the owner condition | Same as unscoped queries |
| Returning internal fields (owner IDs, other users' emails) in responses | Unnecessary exposure |
| Trusting the frontend to hide or disable controls | Frontend is not a security boundary |
| Logging tokens, secrets, or credentials | Secret exposure (Section 8) |
| Committing keys, `.env` files, or credential JSON | Secret exposure (Section 8) |

## 7. Why Client-Supplied Ownership Identifiers Are Not Trusted (S1-BR-010)

Anything sent by the client can be edited by the client: request bodies, query strings, headers, cookies, local storage, and URL paths. A user ID or owner ID in a request is a claim, not proof. If the backend believed it, any signed-in user could change one value and act as someone else.

The only trusted identity is the one the backend derives from the **verified Firebase token**.

Concrete rules:

- `POST /api/targets` has no `owner_id` or `user_id` field. Creation sets `owner_id = current_user.id`. If a client sends one anyway, it is ignored (Pydantic schemas should not define it, and tests send it to prove it is ignored).
- Resource IDs in URLs (`/api/targets/{target_id}`) identify *which* record, never *whose* record. Ownership is always checked separately.
- The frontend never stores or sends the user's database ID for authorization purposes.
- Email addresses and display names are never ownership keys.

## 8. Secrets and Environment Configuration (S1-BR-011)

### 8.1 Rules

- Never commit secrets: API keys, Firebase Admin credentials, database passwords, review-provider keys.
- No environment-specific value is hard-coded in source. Configuration is read from environment variables in `backend/app/config.py` and `frontend/src/lib/config.ts`.
- Commit `.env.example` files with names only. Real values live in untracked `.env` files, a gitignored `secrets/` folder, or CI secret storage.
- `.gitignore` excludes `.env`, `.env.*` (except `.env.example`), `secrets/`, and service-account JSON files.
- A key committed to source control is a security finding even if the repository is private or the key is later deleted. **Response: rotate the key first, then remove it from the repo.**
- The backend fails at startup with a clear message naming any missing required variable.
- Never print secrets in logs, error messages, API responses, screenshots, demos, or AI prompts.

### 8.2 Where each value lives

| Value | Sensitivity | Allowed location |
|---|---|---|
| Firebase Admin service-account credential | Secret | Backend only (`FIREBASE_ADMIN_CREDENTIALS`, untracked file path or CI secret) |
| Review-provider API key | Secret | Backend only (`REVIEW_PROVIDER_API_KEY`) |
| Database credentials (`DATABASE_URL`) | Secret | Backend only |
| Firebase web config (`VITE_FIREBASE_*`) | Public by Firebase design | Frontend env vars; this is the only provider config allowed in browser code |
| `VITE_API_BASE_URL`, `ALLOWED_ORIGINS`, `INGESTION_MAX_REVIEWS` | Non-secret config | Environment variables |

Anything prefixed `VITE_` is bundled into browser code and visible to every user. **Never put a secret in a `VITE_` variable.** The frontend calls the backend; only the backend calls the review provider.

### 8.3 Separation of environments

Development, automated test, and production configuration are separate and selected by environment variables, not by editing source code. Tests never use real credentials.

## 9. Testing Cross-User Isolation (S1-BR-008)

Every endpoint that touches user-owned data ships with isolation tests. CI must run them, and a pull request that adds such an endpoint without them is incomplete.

### 9.1 Test setup

- Use a **fake token verifier** in tests so two distinct identities exist without calling Firebase: a fixture overrides the verification dependency and maps test tokens to `user_a` and `user_b`.
- Fixtures create User A with Target A (and reviews) and User B with Target B.
- Tests use fakes or fixtures for the review provider. No live Firebase, provider, or Claude calls.

```python
def test_user_b_cannot_read_user_a_target(client, user_a_target, user_b_headers):
    res = client.get(f"/api/targets/{user_a_target.id}", headers=user_b_headers)
    assert res.status_code == 404
    assert user_a_target.name not in res.text
```

### 9.2 Required test matrix

| Area | Test | Expected |
|---|---|---|
| Authentication | Each protected endpoint called with no token | `401`, no data in body |
| Authentication | Invalid or expired token | `401` |
| Authentication | Token from before logout (if revocation implemented) | `401` |
| Ownership assignment | Create target while body includes someone else's `owner_id` | Target owned by the authenticated user; client value ignored |
| Persistence | Created target retrieved by owner | Correct values and `owner_id` |
| List isolation | User A lists targets; User B lists targets | Each sees only their own |
| Cross-user read | User B `GET /api/targets/{A's id}` | `404`, no A data |
| Cross-user mutation | User B updates or deletes A's target | `404`; Target A unchanged afterwards |
| Cross-user reviews | User B `GET /api/targets/{A's id}/reviews` | `404`, no reviews returned |
| Cross-user ingestion | User B `POST /api/targets/{A's id}/ingestions` | `404`; provider fake **never called**; no run or reviews created |
| Cross-user review creation | User B import or create reviews under A's target | `404`; nothing persisted |
| Review separation | Target A reviews requested via Target B | Never appear |
| Existence leak | Non-existent target ID vs. A's target ID as User B | Identical status and body |

Always assert that the victim's data is **unchanged** after the attack, not just that the attacker got an error.

### 9.3 Live demonstration

The demo uses User B to request a known User A resource (URL or ID captured earlier) directly in the browser or with `curl` and shows `404` with no User A data. The same behavior is covered by automated tests.

## 10. Checklist for Developers and AI Coding Tools

Before opening a pull request that touches user-owned data, confirm:

- [ ] Every new protected route uses `Depends(get_current_user)`
- [ ] Owner comes from the verified user, not from the request
- [ ] Every query and mutation is owner-scoped (or goes through an owner-scoped parent lookup)
- [ ] Ownership is checked before any provider call, write, or other side effect
- [ ] Missing and not-owned resources return the same `404`
- [ ] No client-sent `owner_id` or `user_id` is read or defined in schemas
- [ ] Cross-user and unauthenticated tests were added, and they assert the victim's data is unchanged
- [ ] No secret, key, token, or `.env` file is committed, logged, or placed in a `VITE_` variable
- [ ] New environment variables are added to `.env.example` (names only)
- [ ] The PR's Test Evidence section lists the isolation tests

**If you are an AI coding tool:** do not generate code that fetches user-owned data by ID alone, accepts an owner ID from the client, filters results on the client, or places credentials in source or frontend code. When unsure whether a query is owner-scoped, make the owner an explicit required parameter and add a cross-user test.

## 11. Sprint 2 Preview (Do Not Build in Sprint 1)

Review content sent to an LLM is protected application data. Later, Q&A context must be built only from reviews of the authenticated user's active target, enforced before the model is called, and stale context from a previously selected target must not persist. The ownership pattern in this document is what that work will build on.
