# AI-Assisted Development and Review

For all team members using AI coding tools on ReviewLens. Story S1-004.

AI-generated code is team-authored code. It meets the same Definition of Done, and the person who submits it must be able to explain it during review and in the demo.

## Tools

Claude Code is in use. Other tools the PRD permits (Cursor, Codex, Copilot) follow the same rules. Add any tool the team adopts to this list.

## Context to supply

Point the tool at what applies to the task:

- The story and its `S1-BR` rules.
- `docs/coding-standards.md` for all code.
- `docs/security-guardrails.md` for anything touching auth, ownership, secrets, or user data.
- `docs/ui-ux-standards.md` for frontend work.
- Existing code that shows the pattern to follow.

Never paste real secrets, `.env` contents, service account keys, or tokens into a tool.

## Reviewing generated code

Before opening a PR, read every line and check that:

- It does what the story requires and nothing from a later sprint.
- It follows existing patterns instead of adding a parallel one.
- Tests would fail if the behavior broke, and weren't weakened to pass.
- Errors shown to users contain no internal detail.

A second team member reviews every PR.

## Validating dependencies and APIs

AI tools can invent packages, functions, and options. Confirm that each new dependency exists on PyPI or npm under that exact name and is maintained. Check unfamiliar APIs against official documentation. Pin versions as `docs/coding-standards.md` describes.

## Required testing

Before generated code is accepted:

1. All lint, format, build, and test checks pass locally and in CI.
2. The new or changed behavior has tests, including the failure path.
3. The feature works in the running app.
4. The PR has a Test Evidence section. For Sprint 2 onward, it also notes changes to prompts, context construction, or guardrails.

## Transcripts

Keep complete transcripts in `ai-transcripts/`, where available from the tool. Don't remove dead ends or failed approaches. Name files `YYYY-MM-DD-<story>-<name>.<ext>`. Check each transcript for secrets before committing it. If one contains a secret, replace only the secret with `[REDACTED]`, and rotate that secret.

## Extra security review

A generated change needs a second reviewer to check it specifically against `docs/security-guardrails.md` when it touches:

- Token verification, `get_current_user`, or user mapping.
- Repository queries on user-owned data.
- Secrets, configuration, CI workflows, or `.gitignore`.
- Ingestion or provider calls.
- Database migrations, especially deletes and cascades.
- From Sprint 2, LLM prompts or context construction.
