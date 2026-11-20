"""Boundary around the language model provider (Anthropic Claude).

Only this module knows about the Anthropic SDK. The Q&A service talks to the
``LLMClient`` protocol in ``app.services.qa``, and tests use ``tests/fake_llm.py``,
so CI never calls a live model.
"""

import logging
from typing import Any

import anthropic

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "claude-sonnet-5-5"
# Medium is enough for reading up to a few hundred short reviews, and keeps
# answers fast for the demo. Set explicitly because defaults vary by model.
EFFORT = "medium"
MAX_OUTPUT_TOKENS = 16000
REQUEST_TIMEOUT_SECONDS = 90.0
# If the provider's safety system declines a request, it reruns it on a backup
# model inside the same call instead of failing.
FALLBACK_BETA = "server-side-fallback-2026-07-01"

DISPOSITIONS = ("answered", "insufficient_evidence", "declined")

# The model must reply in this shape, so the application can tell an answer,
# a lack of evidence and a refusal apart without parsing prose.
ANSWER_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "disposition": {"type": "string", "enum": list(DISPOSITIONS)},
        "answer": {"type": "string"},
        "evidence_review_ids": {"type": "array", "items": {"type": "integer"}},
    },
    "required": ["disposition", "answer", "evidence_review_ids"],
    "additionalProperties": False,
}


class LLMError(Exception):
    """The model could not produce an answer.

    ``category`` is one of: timeout, rate_limited, unavailable, misconfigured,
    refused, unexpected.
    """

    def __init__(self, category: str) -> None:
        super().__init__(category)
        self.category = category


class ClaudeClient:
    """``LLMClient`` implementation backed by the Anthropic Messages API."""

    def __init__(
        self,
        api_key: str,
        model: str = DEFAULT_MODEL,
        client: Any | None = None,
    ) -> None:
        self._client = client or anthropic.Anthropic(
            api_key=api_key, timeout=REQUEST_TIMEOUT_SECONDS, max_retries=2
        )
        self._model = model

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Return the model's JSON reply as text, matching ``ANSWER_SCHEMA``."""
        try:
            response = self._client.beta.messages.create(
                model=self._model,
                max_tokens=MAX_OUTPUT_TOKENS,
                betas=[FALLBACK_BETA],
                fallbacks="default",
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
                output_config={
                    "effort": EFFORT,
                    "format": {"type": "json_schema", "schema": ANSWER_SCHEMA},
                },
            )
        # APITimeoutError is a subclass of APIConnectionError, so it comes first.
        except anthropic.APITimeoutError:
            logger.warning("Model request timed out")
            raise LLMError("timeout") from None
        except anthropic.RateLimitError:
            logger.warning("Model request was rate limited")
            raise LLMError("rate_limited") from None
        except (anthropic.AuthenticationError, anthropic.PermissionDeniedError):
            logger.error("Model API key was rejected; check ANTHROPIC_API_KEY")
            raise LLMError("misconfigured") from None
        except anthropic.APIConnectionError:
            logger.warning("Could not reach the model provider")
            raise LLMError("unavailable") from None
        except anthropic.APIStatusError as exc:
            logger.error("Model request failed with HTTP %s", exc.status_code)
            category = "unavailable" if exc.status_code >= 500 else "unexpected"
            raise LLMError(category) from None

        if response.stop_reason == "refusal":
            logger.warning("Model declined the request (refusal stop reason)")
            raise LLMError("refused")
        if response.stop_reason == "max_tokens":
            logger.error("Model reply was cut off at the output token limit")
            raise LLMError("unexpected")

        text = "".join(block.text for block in response.content if block.type == "text")
        if not text.strip():
            logger.error("Model reply contained no text")
            raise LLMError("unexpected")
        return text
