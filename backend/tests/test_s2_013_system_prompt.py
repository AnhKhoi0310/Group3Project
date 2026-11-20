import pytest

from app.services.qa import _build_system_prompt


@pytest.fixture
def clear_database():
    """Override database cleanup for database-independent prompt tests"""
    yield


def test_prompt_identifies_active_target():
    prompt = _build_system_prompt(
        target_name="Sunrise Coffee",
        platform="google_maps",
    )

    assert "Sunrise Coffee" in prompt
    assert "google_maps" in prompt


def test_prompt_requires_review_only_answers():
    prompt = _build_system_prompt(
        target_name="Sunrise Coffee",
        platform="google_maps",
    )

    assert "only using the review evidence" in prompt
    assert "current request" in prompt


def test_prompt_prohibits_invented_evidence():
    prompt = _build_system_prompt(
        target_name="Sunrise Coffee",
        platform="google_maps",
    )

    assert "Never invent review content" in prompt


def test_prompt_requires_insufficient_evidence_response():
    prompt = _build_system_prompt(
        target_name="Sunrise Coffee",
        platform="google_maps",
    )

    assert "insufficient evidence" in prompt.lower()


def test_prompt_rejects_unrelated_questions():
    prompt = _build_system_prompt(
        target_name="Sunrise Coffee",
        platform="google_maps",
    )

    assert "Decline questions unrelated" in prompt


def test_prompt_treats_reviews_as_untrusted_data():
    prompt = _build_system_prompt(
        target_name="Sunrise Coffee",
        platform="google_maps",
    )

    assert "untrusted data" in prompt
    assert "never override these rules" in prompt


def test_prompt_changes_for_different_targets():
    coffee_prompt = _build_system_prompt(
        target_name="Sunrise Coffee",
        platform="google_maps",
    )

    pizza_prompt = _build_system_prompt(
        target_name="Mario's Pizza",
        platform="yelp",
    )

    assert "Sunrise Coffee" in coffee_prompt
    assert "Mario's Pizza" in pizza_prompt
    assert "Sunrise Coffee" not in pizza_prompt
    assert "google_maps" in coffee_prompt
    assert "yelp" in pizza_prompt
