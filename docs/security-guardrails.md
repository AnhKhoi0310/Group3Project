# Data and Security Guardrails

For developers and AI coding tools. Story S1-003, rules S1-BR-001 to S1-BR-011.

**Every query and mutation on user-owned data must preserve tenant isolation.** A change that can't show this isn't ready to merge.

## Identity provider

We use **Firebase Authentication**. Firebase handles registration, login, sessions, password reset, and duplicate-email rejection. We store no passwords.

Firebase doesn't handle authorization. ReviewLens must verify tokens, map identity to users, and enforce ownership.

## How identity maps to ownership

1. The frontend signs in with the Firebase SDK and sends `Authorization: Bearer <ID token>`.
2. The `get_current_user` dependency verifies the token with the Firebase Admin SDK on every protected request. A missing or invalid token returns 401. If Firebase can't be reached, the request is denied with 503, never allowed through.
3. The verified `uid` maps to a `users` row with a unique `firebase_uid`, created on the first authenticated request.
4. That internal user ID is the only source of ownership.

Logout calls `POST /api/auth/logout`, which revokes the user's Firebase tokens. Token checks include revocation, so a copied token stops working after logout (S1-BR-006). This signs the user out on all of their devices.

## User-scoped entities

| Entity | Ownership |
|---|---|
| AnalysisTarget | Direct, through `owner_id` |
| IngestionRun | Inherited from its target |
| Review | Inherited from its target |

## Where authorization is enforced

In the backend. Repository queries are always filtered by owner, and child resources are authorized through their parent:

```sql
SELECT * FROM analysis_targets WHERE id = :id AND owner_id = :current_user_id
```

Run this check before any other work, including provider calls. Return the same 404 for "doesn't exist" and "belongs to someone else", so that responses don't reveal which IDs exist. Frontend route guards are for user experience only and provide no security.

## Why client-supplied owner IDs aren't trusted

Anyone can edit a request body, query string, or header. If the server accepted a client-supplied `user_id`, any user could act as another. Request schemas must not include `user_id` or `owner_id`, and any sent value is ignored.

## Prohibited patterns

- Loading a target, review, or run by ID without an owner check.
- Fetching all records and filtering them in the browser or in Python.
- Reading ownership from anything other than `get_current_user`.
- A protected route without `get_current_user`.
- Returning 403 for another user's resource, which confirms it exists.
- Calling the review provider from the frontend.
- Fabricating reviews or falling back to sample reviews when ingestion fails.

## Secrets and configuration

| Value | Location |
|---|---|
| Database URL, provider API key, Firebase Admin credential | Backend only: `backend/.env`, `backend/secrets/`, or CI and hosting secrets |
| Firebase web config | Frontend, because it's public by design |

Every `VITE_` variable ships to the browser, so never put a secret in one. Git ignores `.env` files and `secrets/`, and only `.env.example` templates with placeholders are committed. Missing configuration stops the app with a message naming variables, never values.

If a secret is committed, rotate it immediately. Deleting the commit isn't enough.

## Testing cross-user isolation

Backend tests override `get_current_user` with two fake identities, User A and User B. Each user-scoped endpoint needs tests showing:

- An unauthenticated request returns 401 and no protected data.
- User A's own request succeeds.
- User B's request for User A's resource returns 404 with no User A data.
- User B's write or ingestion attempt fails before any processing, and User A's data is unchanged.
- A client-supplied `owner_id` has no effect.
- Reviews from Target A never appear under Target B.
