# Sprint 2: S2-004 scope-guard evaluation set (cases in scope_evaluation_cases.py).
# Demo: test_evaluation_case_through_the_qa_service. Live run: scripts/live_qa_eval.py
# Search a story ID (for example S2-016) to find its tests. Map: docs/testing.md
"""Scope-guard evaluation set (S2-004).

The cases live in scope_evaluation_cases.py and cover in-scope questions,
insufficient evidence, general knowledge, other entities and other platforms.
``evaluate_result`` judges behavior, not wording, and the same judge is used
against the live model by scripts/live_qa_eval.py.
"""

import pytest
from fake_llm import FakeLLM, structured_reply
from scope_evaluation_cases import (
    APP_STATUS,
    EXPECTED_DISPOSITIONS,
    REQUIRED_SCOPE_CATEGORIES,
    SCOPE_EVALUATION_CASES,
    evaluate_result,
)
from test_s2_003_qa_harness import (
    create_review,
    create_successful_ingestion,
    create_target,
    create_user,
)

from app.services.qa import answer_question

CASE_IDS = [case["id"] for case in SCOPE_EVALUATION_CASES]


def case_by_category(category):
    return next(c for c in SCOPE_EVALUATION_CASES if c["category"] == category)


def create_evaluation_dataset(db):
    """Create a persisted dataset used by every evaluation case."""
    user = create_user(db, "s2-004-evaluation-user")
    target = create_target(db, user.id, "Northside Cafe")

    create_successful_ingestion(db, target.id)
    reviews = [
        create_review(
            db,
            target.id,
            "The coffee was excellent and the staff were friendly.",
            rating=5,
        ),
        create_review(
            db,
            target.id,
            "The wait was too long and the service was slow.",
            rating=2,
        ),
    ]
    return user, target, reviews


def controlled_reply(case, reviews):
    """The reply a well-behaved model would give, in the required JSON shape."""
    status = APP_STATUS[case["expected_disposition"]]
    ids = [review.id for review in reviews] if status == "answered" else []
    return structured_reply(status, case["controlled_response"], ids)


# The evaluation set itself


# S2-004: all five question categories are in the set
def test_all_required_categories_are_present():
    categories = {case["category"] for case in SCOPE_EVALUATION_CASES}

    assert REQUIRED_SCOPE_CATEGORIES.issubset(categories)


# S2-004: each category has at least two questions
def test_every_required_category_has_multiple_examples():
    for category in REQUIRED_SCOPE_CATEGORIES:
        matching = [c for c in SCOPE_EVALUATION_CASES if c["category"] == category]

        assert len(matching) >= 2


# S2-004: case IDs are unique
def test_case_ids_are_unique():
    assert len(CASE_IDS) == len(set(CASE_IDS))


# S2-004: each category expects the right outcome
def test_each_category_has_the_correct_expected_disposition():
    for case in SCOPE_EVALUATION_CASES:
        assert case["expected_disposition"] == EXPECTED_DISPOSITIONS[case["category"]]


# S2-004: every case has an ID, a question, a reply, and evidence words where needed
def test_evaluation_cases_have_valid_structure():
    for case in SCOPE_EVALUATION_CASES:
        assert case["id"].strip()
        assert case["question"].strip()
        assert case["controlled_response"].strip()
        assert case["category"] in REQUIRED_SCOPE_CATEGORIES
        assert case["expected_disposition"] in APP_STATUS

        if case["expected_disposition"] == "answer":
            assert case.get("evidence")


# The judge


# S2-004: the judge accepts the correct outcome for every case
@pytest.mark.parametrize("case", SCOPE_EVALUATION_CASES, ids=CASE_IDS)
def test_expected_behavior_is_accepted(case):
    status = APP_STATUS[case["expected_disposition"]]
    cited = 1 if status == "answered" else 0

    assert evaluate_result(case, status, case["controlled_response"], cited) == []


# S2-004, S2-014: the judge flags an answered general-knowledge question
def test_answering_a_general_knowledge_question_is_rejected():
    case = case_by_category("general_knowledge")

    problems = evaluate_result(case, "answered", "The capital is Paris.", 0)

    assert "expected declined, got answered" in problems


# S2-004, S2-012: the judge flags a guess where evidence is missing
def test_guessing_instead_of_reporting_missing_evidence_is_rejected():
    case = case_by_category("insufficient_evidence")

    problems = evaluate_result(case, "answered", "Yes, there is a big lot.", 0)

    assert "expected insufficient_evidence, got answered" in problems


# S2-004, S2-011: the judge flags an answer with no cited reviews
def test_answer_without_review_evidence_is_rejected():
    case = case_by_category("in_scope")

    problems = evaluate_result(case, "answered", "It has a swimming pool.", 0)

    assert "no supporting reviews cited" in problems
    assert "answer mentions none of the expected evidence" in problems


# S2-004, S2-015: the judge flags a decline that cites reviews
def test_declined_answer_that_cites_reviews_is_rejected():
    case = case_by_category("another_platform")

    problems = evaluate_result(case, "declined", "I can't do that.", 2)

    assert problems == ["a declined question cites reviews"]


# S2-004: the judge flags an empty reply
def test_empty_reply_is_rejected():
    case = case_by_category("another_entity")

    assert evaluate_result(case, "declined", "  ", 0) == ["empty answer"]


# S2-004: the judge accepts different wording; no exact sentence is required
def test_different_wording_is_accepted():
    case = case_by_category("in_scope")

    assert evaluate_result(case, "answered", "Reviewers loved the COFFEE.", 1) == []


# Each case through the real orchestration path


# S2-004 (demo): every case runs through the real Q&A service and passes the judge
@pytest.mark.parametrize("case", SCOPE_EVALUATION_CASES, ids=CASE_IDS)
def test_evaluation_case_through_the_qa_service(db, case):
    user, target, reviews = create_evaluation_dataset(db)
    llm = FakeLLM(response=controlled_reply(case, reviews))

    result = answer_question(
        session=db,
        owner_id=user.id,
        target_id=target.id,
        question=case["question"],
        llm=llm,
    )

    assert (
        evaluate_result(case, result.status, result.answer, len(result.evidence)) == []
    )
    assert result.target_id == target.id
    assert result.reviews_used == 2
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
    assert "The coffee was excellent" in user_prompt
    assert "The wait was too long" in user_prompt
