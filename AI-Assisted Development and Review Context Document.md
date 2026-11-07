# AI-Assisted Development and Review Context Document

**Project:** ReviewLens AI (repository: Group3Project) · **Story:** S1-004 · **Rules:** S1-BR-004, S1-BR-008, S1-BR-011

This document outlines our team's guidelines for using AI-assisted coding tools, including how AI-generated code is prompted, reviewed, tested, and approved before merge. The goal is to ensure AI-generated code is reliable, secure, and properly reviewed before merging.

**Core principle:** AI-generated code is team-authored code. It follows the same standards, the same Definition of Done, and the same review as hand-written code. Developers remain responsible for the correctness and security of any code produced with AI assistance. "The AI wrote it" is never an explanation for a defect, and any teammate may be asked in the demo to explain code they submitted.

## 1. AI Coding Tools

Our team plans to use AI-assisted coding tools such as Anthropic Claude to support development. These tools may be used for generating code, debugging, refactoring, writing tests, reviewing code, and explaining technical concepts. All output must be reviewed before being merged into the project.

| Tool | Typical use | Transcript source |
|---|---|---|
| Claude Code | Multi-file implementation, tests, refactors in the repo | Session export or saved log |
| Claude (chat) | Design questions, documents, code review, debugging help | Chat export |
| Other tools the team adopts (Cursor, Codex, Copilot) | As agreed | Export if available; see Section 6 |

*Edit this table to match the tools teammates actually use.*

Rules for all tools:

- Add a new tool to this table (via PR) before using it on project code.
- Never give an AI tool secrets, tokens, credential files, or real user data (S1-BR-011).
- Routine inline autocomplete is allowed and does not need an individual record, but it is reviewed like any other code.

## 2. Context Provided to AI Tools

AI output is only as good as its context. Generic prompts produce generic code that ignores our security rules.

### 2.1 Tech stack (current)

- **Frontend:** React, TypeScript, Tailwind CSS (Vite)
- **Backend:** Python 3.12 and FastAPI
- **Database:** MySQL only (SQLAlchemy and Alembic migrations)
- **Authentication:** Firebase Authentication (managed identity)
- **Review ingestion:** from the target's source URL through a server-side review-provider adapter; CSV/JSON import is only an optional secondary recovery path
- **Later sprints (do not build in Sprint 1):** Anthropic Claude for Q&A (Sprint 2) and AWS deployment (Sprint 3)

The revised Tech Stack and Architecture Baseline replaces the original `techstack.txt` (which listed MongoDB, CSV/JSON upload as the main ingestion method, and a different product shape with organizations, issues, and alerts).

### 2.2 Source-of-truth order

If documents conflict, follow this order:

1. Sprint 1 Stories (scope, canonical rules S1-BR-001 to S1-BR-027)
2. Product Requirements Document
3. UX and Interface Guidance and our UI/UX Standards (S1-002)
4. Technical Specifications
5. Our context documents below

### 2.3 Context pack (keep in `docs/` and give to the tool)

| Document | Suggested file | Give to the tool when |
|---|---|---|
| Sprint 1 Stories | `docs/sprint1-stories.md` | Always |
| Product Requirements Document | `docs/prd.md` | Always (or summarized) |
| Technical Specifications | `docs/technical-specifications.md` | Always |
| Tech Stack and Architecture Baseline | `docs/tech-stack.md` | Always |
| Engineering Coding Standards (S1-001) | `docs/engineering-standards.md` | Always |
| This document (S1-004) | `docs/ai-assisted-development.md` | Always |
| UX and Interface Guidance | `docs/ux-interface-guidance.md` | Frontend work |
| UI/UX Standards (S1-002) | `docs/ui-ux-standards.md` | Frontend work |
| Data and Security Guardrails (S1-003) | `docs/data-and-security-guardrails.md` | Backend work, user-owned data, config, secrets |
| Project Structure and Local Dev Workflow (S1-005) | `docs/project-setup.md` | Setup, environment, tooling, CI |
| Sprint 1 Demo requirements | `docs/sprint1-demo.md` | Planning, seed data, tests, security demo |

If the tool reads a project instruction file (for example `CLAUDE.md`), keep a short one at the repo root that points to these documents and repeats the rules in Section 2.4. Update it whenever a context document changes.

### 2.4 Non-negotiable rules to state in every prompt

1. Every protected backend route uses the shared `get_current_user` dependency (S1-BR-004).
2. Ownership comes only from the verified token. Never read or define `owner_id` or `user_id` in request data (S1-BR-010).
3. Every query and mutation on user-owned data is owner-scoped. Child resources (runs, reviews) are authorized through the owned parent target before any work (S1-BR-007 to S1-BR-009).
4. Missing and not-owned resources return the same `404`.
5. No secrets in source, logs, or `VITE_` variables. Config comes from environment variables; names go in `.env.example` (S1-BR-011).
6. Ingestion starts from the target's source URL. Never fabricate or hard-code reviews. A failed ingestion never deletes valid data (S1-BR-019, S1-BR-024).
7. User-facing errors are plain-language and never expose stack traces, provider text, or Firebase internals.
8. Do not build features outside Sprint 1 scope (no Q&A, LLM calls, summaries or analytics, sentiment, multiple platforms, deployment).
9. Tests never call live Firebase, the review provider, or any LLM.

### 2.5 How to prompt

Prompts should explain the feature being developed, the expected behavior, the relevant data structures, and the existing coding conventions. In addition:

- One focused task per prompt, tied to a story ID and the canonical rule IDs it implements.
- Name the layers or files involved and the existing patterns to copy.
- Ask for the tests in the same request (happy path, error path, and a cross-user test where ownership applies).
- State what must not change. Prefer small diffs; large multi-feature generations are not accepted as one PR.
- Never include API keys, passwords, or authentication tokens.

```text
Story: S1-017 View My Analysis Targets (rules S1-BR-007..010, S1-BR-016)
Context: docs/engineering-standards.md, docs/data-and-security-guardrails.md, docs/tech-stack.md
Task: Add GET /api/targets returning only the authenticated user's targets.
Constraints: use Depends(get_current_user); owner-scoped query in the repository;
  Pydantic response schema; no owner_id accepted from the client.
Tests: owner sees own targets; second user sees only theirs; unauthenticated returns 401.
Do not: add features beyond this story or new dependencies without asking.
```

## 3. Reviewing AI-Generated Code

All AI-generated code must be reviewed by a developer before it is accepted. The review verifies that the code correctly implements the requested functionality, follows the project's architecture, and is readable, maintainable, and free of unnecessary complexity and security vulnerabilities. Developers must understand AI-generated code rather than copying it into the project without verification.

### 3.1 Author self-review (before opening the PR)

- [ ] I read every changed line and can explain it without the AI.
- [ ] It does only what the story asks; no unrequested features, files, or refactors.
- [ ] It follows the Engineering Coding Standards and the UI/UX Standards (for frontend).
- [ ] The rules in Section 2.4 are met.
- [ ] No leftover debug code, commented-out blocks, placeholder or fake data, or TODOs hiding missing behavior.
- [ ] Errors return safe messages and log details server-side.

### 3.2 Teammate review (pull request)

- A teammate other than the author approves, and reads the diff rather than relying on the AI's summary.
- Reviewers watch for common AI failure modes: queries that fetch by ID without the owner condition; invented functions or library APIs; swallowed or overly broad exceptions; tests that assert nothing or mock away the behavior under test; code that special-cases a test to pass; hard-coded sample reviews or users; duplicated helpers instead of reusing existing components and services.
- The PR description states that AI was used, names the tool, and links the transcript.
- The PR includes a **Test Evidence** section.

### 3.3 Merge conditions (enforced by repository settings)

- Required CI checks pass (lint or static checks, build, automated tests).
- At least one approving teammate review.
- No direct pushes to the protected branch.

## 4. Validating Generated Dependencies and APIs

AI tools may suggest outdated libraries, incorrect methods, or APIs that do not exist. Before using AI-generated dependencies or API integrations, developers must:

- [ ] Verify packages through official documentation or the trusted registry (npm or PyPI), checking the name is exact (watch for look-alike names).
- [ ] Check compatibility with the project's existing technologies and the pinned versions.
- [ ] Review the dependency for known security vulnerabilities and confirm it is maintained and appropriately licensed.
- [ ] Confirm that generated API calls use valid endpoints, parameters, and authentication methods, checked against the official documentation of the pinned version.
- [ ] Avoid unnecessary dependencies: do not add a library if the feature can be built simply with what the project already uses. Discuss large UI libraries with the team first.
- [ ] Pin the version and commit the lockfile or requirements change, and state in the PR why the dependency was added.

This applies especially to Firebase Authentication and the Firebase Admin SDK, MySQL and SQLAlchemy and Alembic, the review provider, and (in later sprints) Anthropic Claude and AWS.

For the review provider, record one real response as a test fixture and write the adapter and normalizer against that real shape, not an imagined one. Read generated SQL and migrations, and run them against a local database. If a generated approach cannot be verified in documentation or by running it, do not merge it.

## 5. Required Testing Before Acceptance

AI-generated code must meet the same testing standards as code written manually. Before acceptance, developers must:

- [ ] Confirm the story outcome works in the running application (run it locally using the setup guide).
- [ ] Verify individual functions and components work correctly, and that frontend, backend, database, and external-service boundaries interact correctly.
- [ ] Add or update at least one automated test for the behavior, including negative or edge behavior.
- [ ] **Authentication and authorization:** unauthenticated requests are denied (`401`, no data); cross-user requests are denied (`404`, the other user's data unchanged). See the test matrix in the Data and Security Guardrails.
- [ ] **Validation:** invalid or unexpected input is rejected and not persisted; valid input succeeds.
- [ ] **Persistence:** created data can be read back with the correct owner.
- [ ] **Ingestion:** deterministic fixtures cover a valid review, missing text, missing or invalid rating, and absent optional metadata. Provider timeout, quota, and failure produce distinct, non-fabricating outcomes and leave existing reviews intact. If the optional import path is built, malformed CSV/JSON is handled safely.
- [ ] **Sensitive data:** verify protection of sensitive data (no secrets or tokens in logs, responses, or frontend code).
- [ ] Use fakes, mocks, or recorded fixtures; tests never call live Firebase, the review provider, or an LLM.
- [ ] Confirm each new test fails when the behavior it protects is broken. An AI-written test that cannot fail is not evidence.
- [ ] All required automated tests and code quality checks pass locally and in CI, and existing regression tests still pass.
- [ ] The PR has a Test Evidence section, and significant assumptions or limitations are documented.

## 6. AI Session Transcript Retention

The project requires complete AI-assisted development transcripts, kept in the repository's `ai-transcripts/` folder (the repository is access-controlled, and it is the project's shared record). For significant AI-assisted tasks the team retains the interaction records for transparency and future reference.

- **Naming:** one file per session, `YYYY-MM-DD_<author>_<tool>_<story-or-topic>.md`.
- **Header:** author, tool, date, related story or PR, and a short note of the important changes made to the generated code and key implementation decisions.
- **Contents:** the full prompts and responses, in order. Do not remove dead ends or failed approaches.
- **Redaction:** remove sensitive information (API keys, tokens, credentials, personal data) before committing, and mark the removal `[REDACTED]`. This is the only permitted edit. If a secret appeared in a session, rotate it.
- **Timing:** commit the transcript in the same PR as the code it produced, or the same working day. The PR links it.
- **Routine autocomplete** does not require individual records. Note the tool in the PR if it produced meaningful code.
- If a tool cannot export a transcript, copy the conversation manually or save the closest available record and note the limitation in the file.

## 7. Additional Security Review

Changes in the areas below need review by another qualified team member who has read the Data and Security Guardrails, in addition to the normal approval. The PR must include security notes and show the relevant isolation tests in Test Evidence.

| Trigger | What the reviewer checks |
|---|---|
| Authentication or token verification (Firebase integration, `get_current_user`, logout and revocation) | Tokens verified on every protected request; invalid or missing tokens return `401`; no custom credential handling (S1-BR-001, S1-BR-002, S1-BR-004) |
| Any endpoint, service, or query that reads or writes user-owned data (customer reviews, user information, analysis targets) | Owner-scoped; child resources authorized through the parent; same `404` for missing and not-owned; no client-supplied owner (S1-BR-007 to S1-BR-010) |
| Database operations: repository code, raw SQL, migrations touching ownership columns or foreign keys | Owner condition present; `owner_id` stays `NOT NULL`; cascades correct |
| Review ingestion: provider calls, normalizer, persistence | Ownership verified before the provider is called; no fabricated reviews; failures don't destroy valid data; provider key stays server-side |
| File uploads or import parsing (CSV/JSON recovery path) | Size and type limits; malicious or malformed input handled safely; owner check first |
| Secrets, environment variables, config, CI workflows, `.gitignore` | No secrets committed, logged, or placed in `VITE_` variables; `.env.example` updated (S1-BR-011) |
| Logging or error-handling changes | No tokens, secrets, or bulk review text logged; no stack traces or provider text sent to clients |
| New dependencies, especially auth, HTTP, or file-parsing libraries | Package verified, pinned, maintained, justified |
| CORS, middleware, headers, or rate limiting | Origins restricted through configuration; nothing opened wider than needed |
| Branch protection, required checks, CI gates | Failing required checks still block merge |
| Any change an AI tool made to the files above beyond what was prompted | Unrequested edits are rejected unless explained |
| **Later sprints:** AI integration (sending customer reviews to Claude, handling responses, preventing prompt injection and cross-user or stale context) | Only the active owned target's reviews enter context, enforced before the model call |
| **Later sprints:** infrastructure (AWS configuration, environment variables, API keys, deployment permissions) | Least privilege; secrets in protected storage; deployment downstream of required checks |

If you are unsure whether a change is security-relevant, treat it as relevant.

## 8. Roles and Pre-Demo Alignment

| Role | Responsibility |
|---|---|
| Author | Prompts with the right context, reviews and tests the output, commits the transcript, writes Test Evidence, can explain every line |
| Reviewer | Reads the diff, checks the failure modes in Section 3.2, requires tests, applies Section 7 when triggered |
| Whole team | Keeps the context pack current, rotates leaked secrets immediately, updates this document when practice changes |

The Sprint 1 demo includes questions about code written or modified by specific team members. Each member should be able to explain, without the AI, the stories they implemented, the tests behind them, how the changes passed CI, and the decisions made. AI-generated code nobody on the team can explain is a defect.

## 9. Summary

Our team uses AI coding tools to improve development efficiency while maintaining code quality and security. All AI-generated code must be reviewed, validated, and tested before merging.

- **Before you prompt:** pick one story, attach the context pack, state the Section 2.4 rules, ask for tests.
- **Before you commit:** read every line, run the app, run lint, build, and tests, check dependencies and APIs against official docs, save the transcript.
- **Before you merge:** CI is green, a teammate approved, Test Evidence is in the PR, and security review is done if any Section 7 trigger applies.
