"""Integration tests across ingestion, persistence, summary and Q&A (S2-002).

Each test drives the real API with only the two external services faked: the
review provider (``fetcher``) and the model (``llm``). Everything between them
(normalizing, saving, ownership checks, summary maths, context building) is
the production code.
"""

import pytest
import test_s1_022_s1_023 as s1_helpers
from fake_llm import FakeLLM, structured_reply

from app.adapters.review_source import ReviewSourceError
from app.main import app
from app.routers.questions import get_llm_client

PROVIDER_RECORDS = [
    {"review_id": "r1", "rating": 5, "snippet": "Battery life is superb."},
    {"review_id": "r2", "rating": 4, "snippet": "Battery lasts two days."},
    {"review_id": "r3", "rating": 4, "snippet": "Solid build, decent battery."},
    {"review_id": "r4", "rating": 2, "snippet": "Battery died within a year."},
    {"review_id": "r5", "snippet": "No rating was given here."},
    {"review_id": "r6", "rating": 3},
]
VALID_TEXTS = [record["snippet"] for record in PROVIDER_RECORDS[:4]]


def test_persisted_reviews_can_be_retrieved(client, fetcher):
    target = s1_helpers.create_target(client)

    fetcher.reviews = [
        {"review_id": "r1", "rating": 5, "snippet": "Excellent service"},
        {"review_id": "r2", "rating": 3, "snippet": "Average service"},
    ]

    assert s1_helpers.start(client, target["id"]).status_code == 200

    response = client.get(
        f"/api/targets/{target['id']}/reviews",
        headers=s1_helpers.headers(),
    )

    assert response.status_code == 200
    reviews = response.json()
    assert len(reviews) == 2
    assert {r["text"] for r in reviews} == {
        "Excellent service",
        "Average service",
    }
    assert {r["rating"] for r in reviews} == {3, 5}


def test_ingestion_summary_matches_persisted_reviews(client, fetcher):
    target = s1_helpers.create_target(client)

    fetcher.reviews = [
        {"review_id": "r1", "rating": 5, "snippet": "Great"},
        {"review_id": "r2", "rating": 4, "snippet": "Good"},
        {"review_id": "r3", "rating": 2},
    ]

    response = s1_helpers.start(client, target["id"])
    assert response.status_code == 200

    summary = s1_helpers.latest(client, target["id"])
    assert summary.status_code == 200

    reviews = client.get(
        f"/api/targets/{target['id']}/reviews",
        headers=s1_helpers.headers(),
    )
    assert reviews.status_code == 200

    assert summary.json()["status"] == "succeeded"
    assert summary.json()["reviews_found"] == 2
    assert summary.json()["reviews_skipped"] == 1
    assert len(reviews.json()) == 2


def test_ownership_is_checked_before_review_retrieval(client, fetcher):
    target = s1_helpers.create_target(client, token="token-a")

    fetcher.reviews = [
        {"review_id": "private", "rating": 5, "snippet": "Private review"}
    ]
    assert s1_helpers.start(client, target["id"]).status_code == 200

    owner_response = client.get(
        f"/api/targets/{target['id']}/reviews",
        headers=s1_helpers.headers("token-a"),
    )
    foreign_response = client.get(
        f"/api/targets/{target['id']}/reviews",
        headers=s1_helpers.headers("token-b"),
    )
    missing_response = client.get(
        "/api/targets/999999/reviews",
        headers=s1_helpers.headers("token-b"),
    )

    assert owner_response.status_code == 200
    assert len(owner_response.json()) == 1
    assert foreign_response.status_code == 404
    assert foreign_response.json() == missing_response.json()


def test_switching_targets_returns_different_reviews(client, fetcher):
    target_a = s1_helpers.create_target(client, "Target A")
    target_b = s1_helpers.create_target(client, "Target B")

    fetcher.reviews = [{"review_id": "a1", "rating": 5, "snippet": "Review for A"}]
    assert s1_helpers.start(client, target_a["id"]).status_code == 200

    fetcher.reviews = [{"review_id": "b1", "rating": 2, "snippet": "Review for B"}]
    assert s1_helpers.start(client, target_b["id"]).status_code == 200

    def get_reviews(target_id):
        response = client.get(
            f"/api/targets/{target_id}/reviews",
            headers=s1_helpers.headers(),
        )
        assert response.status_code == 200
        return response.json()

    reviews_a = get_reviews(target_a["id"])
    reviews_b = get_reviews(target_b["id"])
    reviews_a_again = get_reviews(target_a["id"])

    assert [r["text"] for r in reviews_a] == ["Review for A"]
    assert [r["text"] for r in reviews_b] == ["Review for B"]
    assert reviews_a_again == reviews_a


@pytest.fixture
def llm(client):
    """Replace the model for one test; the client fixture restores overrides."""
    fake = FakeLLM(response=structured_reply(answer="From the reviews."))
    app.dependency_overrides[get_llm_client] = lambda: fake
    return fake


def summary_for(client, target_id, token="token-a"):
    return client.get(
        f"/api/targets/{target_id}/summary", headers=s1_helpers.headers(token)
    )


def ask(client, target_id, token="token-a"):
    return client.post(
        f"/api/targets/{target_id}/questions",
        json={"question": "What do customers say about the battery?"},
        headers=s1_helpers.headers(token),
    )


def ingest(client, fetcher, target_id, records):
    fetcher.reviews = records
    response = s1_helpers.start(client, target_id)
    assert response.status_code == 200, response.text
    return response.json()


def test_summary_is_computed_from_the_ingested_reviews(client, fetcher):
    target = s1_helpers.create_target(client, "Phone X")

    attempt = ingest(client, fetcher, target["id"], PROVIDER_RECORDS)
    summary = summary_for(client, target["id"]).json()

    assert (attempt["reviews_found"], attempt["reviews_skipped"]) == (4, 2)
    assert summary["target_name"] == "Phone X"
    assert summary["review_count"] == 4
    assert summary["average_rating"] == 3.8  # (5 + 4 + 4 + 2) / 4
    assert summary["rating_distribution"] == {"1": 0, "2": 1, "3": 0, "4": 2, "5": 1}


def test_qa_context_is_exactly_the_ingested_dataset(client, fetcher, llm):
    target = s1_helpers.create_target(client, "Phone X")
    ingest(client, fetcher, target["id"], PROVIDER_RECORDS)

    answer = ask(client, target["id"]).json()
    summary = summary_for(client, target["id"]).json()

    sent = llm.last_request["user_prompt"]
    for text in VALID_TEXTS:
        assert text in sent
    assert "No rating was given here." not in sent  # skipped records stay out
    assert answer["reviews_used"] == answer["reviews_total"] == 4
    assert answer["reviews_total"] == summary["review_count"]


def test_failed_reingestion_keeps_the_summary_and_qa_dataset(client, fetcher, llm):
    target = s1_helpers.create_target(client, "Phone X")
    ingest(client, fetcher, target["id"], PROVIDER_RECORDS[:2])

    fetcher.error = ReviewSourceError("provider_timeout", "upstream detail")
    assert s1_helpers.start(client, target["id"]).status_code == 504

    summary = summary_for(client, target["id"]).json()
    answer = ask(client, target["id"]).json()

    assert summary["review_count"] == 2
    assert answer["status"] == "answered"
    assert answer["reviews_used"] == 2
    assert "Battery life is superb." in llm.last_request["user_prompt"]


def test_another_user_cannot_read_the_summary_or_ask_questions(client, fetcher, llm):
    target = s1_helpers.create_target(client, "Phone X", token="token-a")
    ingest(client, fetcher, target["id"], PROVIDER_RECORDS)

    foreign_summary = summary_for(client, target["id"], token="token-b")
    missing_summary = summary_for(client, 999999, token="token-b")
    foreign_question = ask(client, target["id"], token="token-b")

    assert foreign_summary.status_code == 404
    assert foreign_summary.json() == missing_summary.json()
    assert foreign_question.status_code == 404
    assert llm.call_count == 0


def test_switching_targets_switches_summary_and_qa_context(client, fetcher, llm):
    phone = s1_helpers.create_target(client, "Phone X")
    store = s1_helpers.create_target(client, "Corner Store")
    ingest(client, fetcher, phone["id"], PROVIDER_RECORDS)
    ingest(
        client,
        fetcher,
        store["id"],
        [{"review_id": "s1", "rating": 1, "snippet": "Customer service was rude."}],
    )

    ask(client, phone["id"])
    ask(client, store["id"])
    store_summary = summary_for(client, store["id"]).json()

    latest = llm.last_request
    assert "Customer service was rude." in latest["user_prompt"]
    assert "Battery" not in latest["user_prompt"]
    assert "Corner Store" in latest["system_prompt"]
    assert "Phone X" not in latest["system_prompt"]
    assert (store_summary["target_name"], store_summary["review_count"]) == (
        "Corner Store",
        1,
    )
