# Sprint 2: S2-014 declining general-knowledge questions.
# Search a story ID (for example S2-016) to find its tests. Map: docs/testing.md
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fake_llm import FakeLLM

from app.services.qa import _build_system_prompt, answer_question


@pytest.fixture
def clear_database():
    """Allow database-independent tests to run without MySQL."""
    yield


# S2-014: sample general-knowledge questions are outside scope
@pytest.mark.parametrize(
    "question",
    [
        "What is the capital of France?",
        "Who invented the telephone?",
        "Write a Python sorting algorithm.",
        "What is 25 multiplied by 8?",
    ],
)
def test_general_knowledge_questions_are_outside_scope(question):
    prompt = _build_system_prompt(
        target_name="Northside Cafe",
        platform="google_maps",
    )

    assert "Do not use general world knowledge" in prompt
    assert "politely explain" in prompt
    assert "Redirect the user" in prompt
    assert "Northside Cafe" in prompt
    assert question not in prompt


# S2-014: refusal instructions name ReviewLens's scope
def test_refusal_instructions_identify_reviewlens_scope():
    prompt = _build_system_prompt(
        target_name="Northside Cafe",
        platform="google_maps",
    )

    assert "only analyzes the active target's supplied reviews" in prompt
    assert "without" in prompt
    assert "unrelated general-knowledge answer" in prompt


# S2-014: refusal instructions apply to every target
def test_refusal_instructions_are_target_independent():
    first_prompt = _build_system_prompt(
        target_name="Northside Cafe",
        platform="google_maps",
    )

    second_prompt = _build_system_prompt(
        target_name="Sunrise Coffee",
        platform="google_maps",
    )

    assert "Northside Cafe" in first_prompt
    assert "Sunrise Coffee" in second_prompt
    assert "Northside Cafe" not in second_prompt

    for prompt in (first_prompt, second_prompt):
        assert "Do not use general world knowledge" in prompt
        assert "Redirect the user" in prompt


# S2-014: a general-knowledge question is sent with the scope instructions
def test_general_knowledge_question_receives_scope_instructions():
    target = SimpleNamespace(
        id=1,
        name="Northside Cafe",
        platform="google_maps",
    )
    review = SimpleNamespace(
        id=10,
        rating=5,
        text="Excellent coffee and friendly staff.",
        reviewer_name="Test Reviewer",
        review_date="2026-11-01",
        source_platform="google_maps",
    )

    llm = FakeLLM(
        response=("I can only analyze the supplied reviews for Northside Cafe.")
    )

    with (
        patch(
            "app.services.qa.get_target_for_owner",
            return_value=target,
        ) as get_target,
        patch(
            "app.services.qa.get_active_reviews_for_target",
            return_value=[review],
        ),
        patch(
            "app.services.qa._has_successful_ingestion",
            return_value=True,
        ),
    ):
        result = answer_question(
            session=MagicMock(),
            owner_id=1,
            target_id=1,
            question="What is the capital of France?",
            llm=llm,
        )

    assert get_target.call_count == 1
    assert get_target.call_args.kwargs["owner_id"] == 1
    assert llm.call_count == 1

    request = llm.last_request

    assert "Northside Cafe" in request["system_prompt"]
    assert "Do not use general world knowledge" in request["system_prompt"]
    assert "Redirect the user" in request["system_prompt"]
    assert "What is the capital of France?" in request["user_prompt"]
    assert "Excellent coffee and friendly staff." in request["user_prompt"]

    assert result.status == "answered"
    assert result.answer == llm.response
