
import json
from pathlib import Path

import pytest


DATA_PATH = Path(__file__).with_name("scope_guard_cases.json")

with DATA_PATH.open(encoding="utf-8") as file:
    DATA = json.load(file)

CASES = DATA["cases"]

REQUIRED_CATEGORIES = {
    "in_scope",
    "insufficient_evidence",
    "world_knowledge",
    "other_target",
    "other_platform",
}

VALID_BEHAVIORS = {
    "answer",
    "insufficient_evidence",
    "out_of_scope",
}


def evaluate_response(case, actual_behavior, response_text):
    if actual_behavior != case["expected"]:
        return False

    if not isinstance(response_text, str):
        return False

    if not response_text.strip():
        return False

    if actual_behavior == "answer":
        evidence = case.get("evidence", [])
        return any(
            word.lower() in response_text.lower()
            for word in evidence
        )

    return True


def test_all_required_categories_exist():
    categories = {case["category"] for case in CASES}

    assert REQUIRED_CATEGORIES.issubset(categories)


def test_multiple_examples_per_category():
    for category in REQUIRED_CATEGORIES:
        matching = [
            case for case in CASES
            if case["category"] == category
        ]

        assert len(matching) >= 2


def test_unique_case_ids():
    ids = [case["id"] for case in CASES]

    assert len(ids) == len(set(ids))


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["id"])
def test_evaluation_case_structure(case):
    assert case["category"] in REQUIRED_CATEGORIES
    assert case["expected"] in VALID_BEHAVIORS
    assert case["question"].strip()

    if case["expected"] == "answer":
        assert case.get("evidence")


def test_evaluator_accepts_valid_response():
    case = CASES[0]

    assert evaluate_response(
        case,
        "answer",
        "Customers appreciate the pizza and friendly staff."
    )


def test_evaluator_rejects_wrong_behavior():
    case = CASES[0]

    assert not evaluate_response(
        case,
        "out_of_scope",
        "I cannot answer this question."
    )


def test_evaluator_accepts_different_wording():
    case = CASES[0]

    assert evaluate_response(
        case,
        "answer",
        "Reviewers frequently compliment the atmosphere."
    )


def test_evaluator_rejects_empty_response():
    case = CASES[0]

    assert not evaluate_response(
        case,
        "answer",
        ""
    )
