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

VALID_DISPOSITIONS = {
    "answer",
    "insufficient_evidence",
    "refuse",
}

INSUFFICIENT_EVIDENCE_MARKERS = (
    "not enough",
    "insufficient",
    "do not contain enough",
    "does not contain enough",
    "do not provide enough",
)

REFUSAL_MARKERS = (
    "cannot",
    "can't",
    "unable",
    "outside my scope",
    "outside the scope",
    "not within my scope",
    "do not have information",
    "does not contain",
    "do not contain",
    "not available in",
    "cannot provide",
    "can only analyze",
)

SCOPE_MARKERS = (
    "active review",
    "active dataset",
    "active target",
    "supplied reviews",
    "reviewlens",
    "review platform",
    "general geography",
    "general-knowledge",
    "general knowledge",
    "general-purpose code",
    "another restaurant",
    "riverside restaurant",
    "brand b",
    "google maps",
    "tripadvisor",
)


def create_evaluation_dataset(db):
    """Create a persisted dataset used by every evaluation case."""
    user = create_user(db, "s2-004-evaluation-user")
    target = create_target(db, user.id, "Northside Cafe")

    create_successful_ingestion(db, target.id)

    create_review(
        db,
        target.id,
        "The coffee was excellent and the staff were friendly.",
        rating=5,
    )
    create_review(
        db,
        target.id,
        "The wait was too long and the service was slow.",
        rating=2,
    )

    return user, target


def evaluate_response(case, response_text):
    """
    Evaluate a response against the intended disposition.

    This deliberately checks behavioral indicators rather than requiring
    one exact natural-language response.
    """
    if not isinstance(response_text, str) or not response_text.strip():
        return False

    response = response_text.casefold()
    disposition = case["expected_disposition"]

    if disposition == "answer":
        evidence = case.get("evidence", [])
        return any(term.casefold() in response for term in evidence)

    if disposition == "insufficient_evidence":
        return any(marker in response for marker in INSUFFICIENT_EVIDENCE_MARKERS)

    if disposition == "refuse":
        has_refusal = any(marker in response for marker in REFUSAL_MARKERS)
        identifies_scope = any(marker in response for marker in SCOPE_MARKERS)
        return has_refusal and identifies_scope

    return False


def test_all_required_categories_are_present():
    categories = {case["category"] for case in SCOPE_EVALUATION_CASES}

    assert REQUIRED_SCOPE_CATEGORIES.issubset(categories)


def test_every_required_category_has_multiple_examples():
    for category in REQUIRED_SCOPE_CATEGORIES:
        matching_cases = [
            case for case in SCOPE_EVALUATION_CASES if case["category"] == category
        ]

        assert len(matching_cases) >= 2


def test_case_ids_are_unique():
    case_ids = [case["id"] for case in SCOPE_EVALUATION_CASES]

    assert len(case_ids) == len(set(case_ids))


def test_each_category_has_the_correct_expected_disposition():
    for case in SCOPE_EVALUATION_CASES:
        assert case["expected_disposition"] == EXPECTED_DISPOSITIONS[case["category"]]


def test_evaluation_cases_have_valid_structure():
    for case in SCOPE_EVALUATION_CASES:
        assert case["id"].strip()
        assert case["question"].strip()
        assert case["controlled_response"].strip()
        assert case["category"] in REQUIRED_SCOPE_CATEGORIES
        assert case["expected_disposition"] in VALID_DISPOSITIONS

        if case["expected_disposition"] == "answer":
            assert case.get("evidence")


@pytest.mark.parametrize(
    "case",
    SCOPE_EVALUATION_CASES,
    ids=[case["id"] for case in SCOPE_EVALUATION_CASES],
)
def test_controlled_response_matches_expected_disposition(case):
    assert evaluate_response(
        case,
        case["controlled_response"],
    )


def test_evaluator_rejects_answer_without_review_evidence():
    case = SCOPE_EVALUATION_CASES[0]

    assert not evaluate_response(
        case,
        "The restaurant has a swimming pool.",
    )


def test_evaluator_rejects_general_knowledge_answer():
    case = next(
        case
        for case in SCOPE_EVALUATION_CASES
        if case["category"] == "general_knowledge"
    )

    assert not evaluate_response(
        case,
        "The capital of France is Paris.",
    )


def test_evaluator_rejects_refusal_without_scope_explanation():
    case = next(
        case
        for case in SCOPE_EVALUATION_CASES
        if case["category"] == "another_platform"
    )

    assert not evaluate_response(
        case,
        "I cannot do that.",
    )


def test_evaluator_accepts_different_wording():
    case = SCOPE_EVALUATION_CASES[0]

    assert evaluate_response(
        case,
        "Reviewers complimented the coffee and described it positively.",
    )


@pytest.mark.parametrize(
    "case",
    SCOPE_EVALUATION_CASES,
    ids=[case["id"] for case in SCOPE_EVALUATION_CASES],
)
def test_evaluation_question_uses_active_target_context(db, case):
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
    assert llm.call_count == 1

    assert evaluate_response(case, result.answer)

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
    assert "The coffee was excellent" in user_prompt
    assert "The wait was too long" in user_prompt
