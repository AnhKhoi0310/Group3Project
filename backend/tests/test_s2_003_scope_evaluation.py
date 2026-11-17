import pytest
from fake_llm import FakeLLM
from scope_evaluation_cases import (
    EXPECTED_DISPOSITIONS,
    REQUIRED_SCOPE_CATEGORIES,
    SCOPE_EVALUATION_CASES,
)
from test_s2_003_qa_harness import (
    create_review,
    create_successful_ingestion,
    create_target,
    create_user,
)

from app.services.qa import answer_question


def create_evaluation_dataset(db):
    """Create a target with representative review evidence."""
    user = create_user(db, "scope-evaluation-user")
    target = create_target(db, user.id, "Northside Cafe")

    create_successful_ingestion(db, target.id)

    create_review(
        db,
        target.id,
        "The coffee was excellent.",
        rating=5,
    )
    create_review(
        db,
        target.id,
        "The wait was too long.",
        rating=2,
    )

    return user, target


def test_evaluation_set_covers_required_categories():
    categories = {case["category"] for case in SCOPE_EVALUATION_CASES}

    assert REQUIRED_SCOPE_CATEGORIES <= categories

    for category in REQUIRED_SCOPE_CATEGORIES:
        matching_cases = [
            case for case in SCOPE_EVALUATION_CASES if case["category"] == category
        ]
        assert len(matching_cases) >= 2


def test_evaluation_cases_have_valid_dispositions():
    for case in SCOPE_EVALUATION_CASES:
        assert case["expected_disposition"] in EXPECTED_DISPOSITIONS.values()
        assert case["question"].strip()
        assert case["controlled_response"].strip()


@pytest.mark.parametrize(
    "case",
    SCOPE_EVALUATION_CASES,
    ids=[case["id"] for case in SCOPE_EVALUATION_CASES],
)
def test_scope_evaluation_cases_use_only_active_target_context(db, case):
    user, target = create_evaluation_dataset(db)
    llm = FakeLLM(response=case["controlled_response"])

    result = answer_question(
        session=db,
        owner_id=user.id,
        target_id=target.id,
        question=case["question"],
        llm=llm,
    )

    assert result.status == "answered"
    assert result.target_id == target.id
    assert result.reviews_used == 2
    assert result.answer == case["controlled_response"]
    assert llm.call_count == 1

    system_prompt = llm.last_request["system_prompt"]
    user_prompt = llm.last_request["user_prompt"]

    assert "Northside Cafe" in system_prompt
    assert "google_maps" in system_prompt
    assert "only using the review evidence" in system_prompt
    assert "Do not use general world knowledge" in system_prompt
    assert "another entity or review platform" in system_prompt
    assert "insufficient evidence" in system_prompt
    assert "Decline questions unrelated" in system_prompt

    assert case["question"] in user_prompt
    assert "The coffee was excellent." in user_prompt
    assert "The wait was too long." in user_prompt
