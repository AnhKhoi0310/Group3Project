# Review Q&A design

How ReviewLens answers questions about a target's reviews (Sprint 2, S2-008 to S2-012). Read this before changing the prompt, the context, or the model call.

## Request flow

`POST /api/targets/{target_id}/questions` with `{"question": "..."}`

1. `get_current_user` identifies the caller from the Firebase token.
2. `answer_question` in `backend/app/services/qa.py` loads the target with the owner filter. A target that doesn't exist or belongs to someone else returns the same 404, and the model is never called.
3. Reviews come from `get_active_reviews_for_target`, the same function the ingestion summary uses, so the summary and Q&A always describe the same dataset (S2-008).
4. If the target has no reviews or no successful ingestion, the service returns `insufficient_evidence` with `reviews_used: 0` and does not call the model.
5. Otherwise the service builds a system prompt for this target, puts the question and reviews in the user message, and calls the `LLMClient`.
6. The reply is checked and returned with the reviews it cited.

Nothing is cached between questions. Each request rebuilds context from the database for the target in the URL, so switching targets can't leave old reviews in the context.

## Context strategy (S2-010)

Decision: **send the target's reviews directly, with no retrieval step.**

- Ingestion collects at most `INGESTION_MAX_REVIEWS` (default 50) per run, so a target holds tens to low hundreds of short reviews.
- At most `MAX_CONTEXT_REVIEWS` (200) are sent, newest first. That is roughly 30,000 input tokens, well inside the model's context window, so there's no need for embeddings or a vector database (S2-BR-013).
- If a target has more than 200 reviews, only the newest 200 are sent. The response reports `reviews_used` and `reviews_total`, and the UI says "Based on the 200 most recent of N reviews". Nothing is dropped silently.
- Revisit this choice if targets regularly exceed 200 reviews, for example by selecting reviews relevant to the question.

## Prompt (S2-013 to S2-015)

The system prompt lives in `_build_system_prompt` in `qa.py`, under version control. It names the active target and platform, limits answers to the supplied reviews, requires an explicit "insufficient evidence" response, and says to decline general-knowledge questions and questions about other entities or platforms. Review text is marked as untrusted data, so instructions written inside a review can't override the rules.

Rule 5 makes the model separate what the reviews support from what they don't cover (S2-012). Rule 10 defines the reply format below.

## Model call

The Claude adapter is `backend/app/adapters/llm.py`. Only this file imports the Anthropic SDK.

| Setting | Value | Why |
|---|---|---|
| Model | `claude-sonnet-5-5` (`LLM_MODEL`) | Team choice: fast and inexpensive for review Q&A. Change it in `backend/.env` without a code change. |
| Effort | `medium` | Reading a few hundred short reviews doesn't need deeper reasoning, and answers stay fast for the demo. |
| Output | JSON schema `ANSWER_SCHEMA` | The app reads a `disposition` instead of guessing from prose. |
| Refusal fallback | `fallbacks: "default"` (beta `server-side-fallback-2026-07-01`) | If the provider's safety system declines a request, it reruns on a backup model in the same call. |
| Timeout and retries | 90 seconds, 2 retries | The SDK retries 429, 5xx and connection errors. |

Reply format:

```json
{"disposition": "answered | insufficient_evidence | declined",
 "answer": "text shown to the user",
 "evidence_review_ids": [12, 15]}
```

`evidence_review_ids` are filtered against the reviews sent with this question. An ID from another target, another user, or one the model invented is dropped, so the UI can only show evidence that was really in the context (S2-BR-010). Declined answers never show evidence.

## Errors

Provider details go to server logs only. Users get the standard error shape.

| Situation | HTTP | `code` |
|---|---|---|
| `ANTHROPIC_API_KEY` not set, or rejected | 503 | `qa_unavailable` |
| Provider unreachable or 5xx | 503 | `qa_unavailable` |
| Timeout | 504 | `qa_timeout` |
| Rate limited | 429 | `qa_busy` |
| Reply cut off, empty, or other 4xx | 502 | `qa_failed` |
| Safety refusal with no fallback | 200 | answer `status: declined` |

## Configuration

`backend/.env`:

- `ANTHROPIC_API_KEY`: optional. Without it the app runs normally, and asking a question returns `qa_unavailable`.
- `LLM_MODEL`: optional, defaults to `claude-sonnet-5-5`.

Each developer needs their own key for live Q&A. Never commit it or send it in chat.

## Testing

CI never calls a live model (S2-BR-029).

- `tests/fake_llm.py` records each prompt and returns a fixed reply. API tests swap it in by overriding the `get_llm_client` dependency.
- `tests/test_s2_009_012_review_qa.py` covers the endpoint on MySQL: cited evidence, insufficient evidence on a known dataset, declines, cross-user and cross-target evidence filtering, the 404 for another user's target, validation, the context cap, summary and Q&A agreeing, target switching, and each error code.
- `tests/test_llm_adapter.py` tests the adapter against a fake SDK client: request shape, error mapping, and refusal handling.
- The scope-guard evaluation set is in `tests/scope_evaluation_cases.py`.
