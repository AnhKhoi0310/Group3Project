"""Deterministic stand-ins for the language model boundary (S2-003).

Tests pass these wherever the app expects an ``LLMClient``, either directly to
``answer_question`` or through ``app.dependency_overrides[get_llm_client]``.
They record every prompt, so a test can inspect exactly which instructions and
reviews would have reached the model. CI never calls a live model.
"""

import json
from collections.abc import Iterable
from dataclasses import dataclass, field

from app.adapters.llm import LLMError


@dataclass
class FakeLLM:
    """Deterministic replacement for the real language model boundary."""

    response: str = "This is a deterministic test answer."
    requests: list[dict[str, str]] = field(default_factory=list)

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Record the request and return a controlled response."""
        self.requests.append(
            {
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
            }
        )
        return self.response

    @property
    def call_count(self) -> int:
        return len(self.requests)

    @property
    def last_request(self) -> dict[str, str] | None:
        if not self.requests:
            return None
        return self.requests[-1]


@dataclass
class FailingLLM(FakeLLM):
    """Records the request, then fails the way the real adapter would."""

    category: str = "unavailable"

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        super().generate(system_prompt, user_prompt)
        raise LLMError(self.category)


def structured_reply(
    disposition: str = "answered",
    answer: str = "Customers praise the pasta.",
    ids: Iterable[int] = (),
) -> str:
    """Build a reply in the JSON shape the real model is required to return."""
    return json.dumps(
        {
            "disposition": disposition,
            "answer": answer,
            "evidence_review_ids": list(ids),
        }
    )
