from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fake_llm import FakeLLM

from app.services.qa import _build_system_prompt, answer_question


@pytest.fixture
def clear_database():
    """Allow database-independent tests to run without MySQL."""
    yield


@pytest.mark.parametrize(
    "question",
    [
        "What do customers think about Riverside Restaurant?",
        "Are customers satisfied with Brand B?",
        "Is another restaurant better than this one?",
    ],
)
def test_other_entity_questions_receive_scope_instructions(question):
    prompt = _build_system_prompt(
        target_name="Northside Cafe",
        platform="google_maps",
    )

    assert "Northside Cafe" in prompt
    assert "politely decline to answer about that other entity" in prompt
    assert "only analyzes the active AnalysisTarget's supplied reviews" in prompt
    assert question not in prompt


@pytest.mark.parametrize(
    "question",
    [
        "What do Northside Cafe's Yelp reviews say?",
        "Summarize the TripAdvisor reviews.",
        "What is Northside Cafe's rating on Trustpilot?",
    ],
)
def test_other_platform_questions_receive_scope_instructions(question):
    prompt = _build_system_prompt(
        target_name="Northside Cafe",
        platform="google_maps",
    )

    assert "google_maps" in prompt
    assert "reviews or ratings from another platform" in prompt
    assert "included in the supplied evidence" in prompt
    assert question not in prompt


def test_entity_mentions_do_not_establish_evidence():
    prompt = _build_system_prompt(
        target_name="Northside Cafe",
        platform="google_maps",
    )

    assert "Do not infer information about another entity or platform merely" in prompt
    assert "because its name appears in a review" in prompt


def test_prompt_changes_with_active_target():
    first = _build_system_prompt("Northside Cafe", "google_maps")
    second = _build_system_prompt("Riverside Restaurant", "yelp")

    assert "Northside Cafe" in first
    assert "Riverside Restaurant" in second
    assert "Northside Cafe" not in second
    assert "google_maps" in first
    assert "yelp" in second


def test_other_entity_question_sends_active_target_to_model():
    target = SimpleNamespace(
        id=1,
        name="Northside Cafe",
        platform="google_maps",
    )
    review = SimpleNamespace(
        id=10,
        rating=5,
        text="The coffee was excellent.",
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
        ),
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
            question="What do customers think of Riverside Restaurant?",
            llm=llm,
        )

    assert llm.call_count == 1
    assert "Northside Cafe" in llm.last_request["system_prompt"]
    assert "google_maps" in llm.last_request["system_prompt"]
    assert "Riverside Restaurant?" in llm.last_request["user_prompt"]
    assert "The coffee was excellent." in llm.last_request["user_prompt"]
    assert result.answer == llm.response


def test_other_platform_question_sends_platform_to_model():
    target = SimpleNamespace(
        id=2,
        name="Northside Cafe",
        platform="google_maps",
    )
    review = SimpleNamespace(
        id=11,
        rating=4,
        text="Friendly staff.",
        reviewer_name="Reviewer",
        review_date="2026-11-01",
        source_platform="google_maps",
    )
    llm = FakeLLM(response="I can only analyze the supplied Google Maps reviews.")

    with (
        patch(
            "app.services.qa.get_target_for_owner",
            return_value=target,
        ),
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
            target_id=2,
            question="What do the Yelp reviews say?",
            llm=llm,
        )

    assert llm.call_count == 1
    assert "google_maps" in llm.last_request["system_prompt"]
    assert "Yelp reviews" in llm.last_request["user_prompt"]
    assert "Friendly staff." in llm.last_request["user_prompt"]
    assert result.answer == llm.response
