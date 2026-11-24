# Testing and coverage

How ReviewLens is tested, what CI enforces, and how to run the same checks on your machine (Sprint 2, S2-001 to S2-004).

## What CI runs on every pull request

Both jobs must pass before a PR can merge into `main`.

| Job | Steps |
|---|---|
| Backend checks | Ruff lint, Ruff format check, compile, `pytest` with coverage on MySQL 8.4, changed-code coverage gate |
| Frontend checks | ESLint, Prettier check, TypeScript and Vite build, Vitest with coverage, changed-code coverage gate |

## Changed-code coverage gate (S2-001)

**Mechanism:** each job measures line coverage, then [diff-cover](https://github.com/Bachmann1234/diff_cover) compares it with the lines the PR adds or changes against its base branch.

| | Coverage tool | Report |
|---|---|---|
| Backend | `pytest-cov` | `backend/coverage.xml` |
| Frontend | Vitest with `@vitest/coverage-v8` | `frontend/coverage/cobertura-coverage.xml` |

**Policy:** at least **80% of changed lines** must be run by a test, checked separately for the backend and the frontend. Untouched old code doesn't count, so the gate holds new work to the standard without blocking on history. It runs on pull requests only.

**Known weakness:** the 80% is for the PR as a whole, not per file. A large PR with well-tested code can hide a small untested function. In one measured case, an untested 7-line function inside a large PR still left the total at 93%. On its own in a small PR, the same function scored 16% and failed the gate. To keep the gate meaningful:

- Keep PRs to one story.
- Reviewers read the per-file lines in the CI log ("Missing lines …") and ask for tests on anything important that's listed.

**Exclusions:**

| Excluded | Why |
|---|---|
| Backend: everything outside `backend/app/` (tests, `migrations/`, `scripts/`) | Only application code is measured. Migrations are checked by `test_models_match_the_migrations`, and scripts are manual tools. |
| Frontend: `*.test.ts(x)`, `*.spec.ts(x)`, `src/test/**`, `*.d.ts` | Tests, test helpers and type declarations aren't application code. |

There are no other exclusions and no `# pragma: no cover` markers. Add one only with a reason in the PR.

## Running the checks locally

Most backend tests need MySQL. Start a separate test database that the tests are allowed to erase:

```
docker run -d --rm --name reviewlens-test -e MYSQL_ROOT_PASSWORD=test -e MYSQL_DATABASE=reviewlens_test -p 127.0.0.1:3317:3306 mysql:8.4
```

Backend, from `backend/` (macOS/Linux: `export TEST_DATABASE_URL=...`):

```
set TEST_DATABASE_URL=mysql+pymysql://root:test@127.0.0.1:3317/reviewlens_test
pytest --cov=app --cov-report=xml:coverage.xml --cov-report=term-missing
diff-cover coverage.xml --compare-branch=origin/main --fail-under=80
```

Frontend, from `frontend/`:

```
npm run test:coverage
diff-cover coverage/cobertura-coverage.xml --compare-branch=origin/main --fail-under=80
```

`diff-cover` comes with the backend dev requirements (`pip install -r requirements-dev.txt`). Run `git fetch origin` first so `origin/main` is current. New files are only counted once git knows about them, so run `git add` (or `git add -N`) before the gate.

Without `TEST_DATABASE_URL`, the tests that need MySQL are skipped and everything else still runs. CI always sets it, and fails if it's missing.

## Integration tests (S2-002)

`backend/tests/test_s2_002_integration.py` drives the real API with only two fakes: the review provider and the model. Everything in between is production code: normalizing, saving, ownership checks, summary maths and context building. These tests cover:

- reviews collected by ingestion are the ones listed, summarized and sent to Q&A
- skipped records never reach the summary or the model
- a failed re-ingestion leaves the summary and Q&A dataset unchanged
- another user gets the same 404 as a missing target, for the summary and for questions, and the model is never called
- switching targets switches the summary and the model context

`backend/tests/test_s2_009_012_review_qa.py` covers the Q&A endpoint in more detail.

## Deterministic Q&A harness (S2-003)

CI never calls a live model and never depends on its wording (S2-BR-029). `backend/tests/fake_llm.py` provides:

| Helper | Use |
|---|---|
| `FakeLLM` | Records every system prompt and user prompt, and returns a fixed reply. `last_request` and `call_count` let a test check which instructions and reviews would have reached the model, or that it was never called. |
| `structured_reply(...)` | Builds a reply in the JSON shape the real model must return (`disposition`, `answer`, `evidence_review_ids`). |
| `FailingLLM(category=...)` | Fails like the real adapter (`timeout`, `rate_limited`, `unavailable`, `refused`, …). |

Use them directly with `answer_question(...)` (see `test_s2_003_qa_harness.py`), or through the API with `app.dependency_overrides[get_llm_client] = lambda: fake`. The real adapter is tested against a fake Anthropic SDK client in `test_llm_adapter.py`.

## Scope-guard evaluation set (S2-004)

- **Cases:** `backend/tests/scope_evaluation_cases.py` has 16 questions across five categories: in-scope, insufficient evidence, general knowledge, another entity, and another platform. There are at least three per category, including an ordinary-sounding comparison question.
- **Judge:** `evaluate_result(case, status, answer, cited_reviews)` decides whether a reply is acceptable from behavior, not wording. It checks that the reported disposition matches, that answers cite supplied reviews and mention the expected evidence, and that declined answers cite nothing.
- **In CI:** `test_s2_004_scope_guard_evaluation.py` runs every case through the real Q&A service with controlled replies. It also checks that the judge rejects bad behavior, such as answering a general-knowledge question or guessing when evidence is missing.
- **Against the live model:** the same cases and judge run with `python scripts/live_qa_eval.py` from `backend/`. It needs `ANTHROPIC_API_KEY`, makes one paid call per case, and isn't part of CI (S2-BR-031). Run it after changing the prompt or the model, and before the demo.

## Sprint 2 test map

Every Sprint 2 test has a one-line comment above it starting with its story ID, and each file opens with a short header. Search a story ID across `backend/tests` and `frontend/src` (in VS Code: Ctrl+Shift+F, for example `S2-016`) to list its tests. Tests marked `(demo)` are the ones to open during the demo. Extras that aren't a story use the tags `Photos:`, `Reviews:` and `Chat dock:`.

| Story | What it covers | Backend (`backend/tests/`) | Frontend (`frontend/src/`) |
|---|---|---|---|
| S2-001 | Changed-code coverage gate | CI step in `.github/workflows/ci.yml` | Same workflow |
| S2-002 | Integration tests | `test_s2_002_integration.py` | |
| S2-003 | Deterministic Q&A harness | `fake_llm.py`, `test_s2_003_qa_harness.py` | |
| S2-004 | Scope-guard evaluation set | `scope_evaluation_cases.py`, `test_s2_004_scope_guard_evaluation.py`, `scripts/live_qa_eval.py` | |
| S2-005 | Ingestion status | `test_s2_009_012_review_qa.py` | `pages/TargetWorkspacePage.test.tsx` |
| S2-006 | Review count and rating summary | `test_target_workspace_api.py`, `test_s2_002_integration.py` | `pages/TargetWorkspacePage.test.tsx` |
| S2-007 | Skipped records | `test_s2_002_integration.py` | `pages/TargetWorkspacePage.test.tsx` |
| S2-008 | Summary from the saved dataset | `test_target_workspace_api.py`, `test_s2_009_012_review_qa.py` | `pages/TargetWorkspacePage.test.tsx` |
| S2-009 | Q&A interface | `test_s2_009_012_review_qa.py`, `test_llm_adapter.py` | `components/QuestionPanel.test.tsx`, `components/QuestionPanel.states.test.tsx` |
| S2-010 | Review context for Q&A | `test_s2_009_012_review_qa.py`, `test_s2_003_qa_harness.py` | `components/QuestionPanel.test.tsx` |
| S2-011 | Answers from review evidence | `test_s2_009_012_review_qa.py`, `test_llm_adapter.py` | `components/QuestionPanel*.test.tsx` |
| S2-012 | Insufficient evidence | `test_s2_009_012_review_qa.py`, `test_s2_013_system_prompt.py` | `components/QuestionPanel*.test.tsx` |
| S2-013 | System prompt | `test_s2_013_system_prompt.py` | |
| S2-014 | Declining general knowledge | `test_s2_014_general_knowledge.py` | `components/QuestionPanel*.test.tsx` |
| S2-015 | Declining other entities and platforms | `test_s2_015_entity_platform.py` | `components/QuestionPanel.test.tsx` |
| S2-016 | Cross-user isolation in AI context | `test_s2_016_cross_user_isolation.py`, `test_s2_009_012_review_qa.py` | |
| S2-017 | Switching the active target | | `components/TargetSwitcher.test.tsx` |
| S2-018 | Q&A context follows the target | `test_s2_009_012_review_qa.py`, `test_s2_002_integration.py` | `pages/TargetSwitchFlow.test.tsx` |
| S2-019 | No stale review context | `test_s2_009_012_review_qa.py`, `test_s2_003_qa_harness.py` | |
| S2-020 | Target without review data | `test_s2_009_012_review_qa.py`, `test_s2_003_qa_harness.py` | `components/QuestionPanel.states.test.tsx`, `pages/TargetWorkspaceQA.test.tsx` |

**Demo tests**, in the order the demo script uses them:

1. `test_s2_002_integration.py` :: `test_qa_context_is_exactly_the_ingested_dataset`
2. `test_s2_003_qa_harness.py` :: `test_controlled_model_response_is_returned_to_the_application`
3. `test_s2_004_scope_guard_evaluation.py` :: `test_evaluation_case_through_the_qa_service`
4. `test_s2_009_012_review_qa.py` :: `test_switching_targets_sends_only_the_new_targets_reviews`
5. `test_s2_016_cross_user_isolation.py` :: `test_user_a_context_excludes_user_b_reviews`
6. `frontend/src/pages/TargetSwitchFlow.test.tsx`
