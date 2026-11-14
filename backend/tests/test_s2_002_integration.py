
import pytest

from test_s1_022_s1_023 import (
    client,
    clear_database,
    create_target,
    fetcher,
    headers,
    latest,
    start,
)


def test_persisted_reviews_can_be_retrieved(client, fetcher):
    target = create_target(client)

    fetcher.reviews = [
        {"review_id": "r1", "rating": 5, "snippet": "Excellent service"},
        {"review_id": "r2", "rating": 3, "snippet": "Average service"},
    ]

    assert start(client, target["id"]).status_code == 200

    response = client.get(
        f"/api/targets/{target['id']}/reviews",
        headers=headers(),
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
    target = create_target(client)

    fetcher.reviews = [
        {"review_id": "r1", "rating": 5, "snippet": "Great"},
        {"review_id": "r2", "rating": 4, "snippet": "Good"},
        {"review_id": "r3", "rating": 2},
    ]

    response = start(client, target["id"])
    assert response.status_code == 200

    summary = latest(client, target["id"])
    assert summary.status_code == 200

    reviews = client.get(
        f"/api/targets/{target['id']}/reviews",
        headers=headers(),
    )
    assert reviews.status_code == 200

    assert summary.json()["status"] == "succeeded"
    assert summary.json()["reviews_found"] == 2
    assert summary.json()["reviews_skipped"] == 1
    assert len(reviews.json()) == 2


def test_ownership_is_checked_before_review_retrieval(client, fetcher):
    target = create_target(client, token="token-a")

    fetcher.reviews = [
        {"review_id": "private", "rating": 5, "snippet": "Private review"}
    ]
    assert start(client, target["id"]).status_code == 200

    owner_response = client.get(
        f"/api/targets/{target['id']}/reviews",
        headers=headers("token-a"),
    )
    foreign_response = client.get(
        f"/api/targets/{target['id']}/reviews",
        headers=headers("token-b"),
    )
    missing_response = client.get(
        "/api/targets/999999/reviews",
        headers=headers("token-b"),
    )

    assert owner_response.status_code == 200
    assert len(owner_response.json()) == 1
    assert foreign_response.status_code == 404
    assert foreign_response.json() == missing_response.json()


def test_switching_targets_returns_different_reviews(client, fetcher):
    target_a = create_target(client, "Target A")
    target_b = create_target(client, "Target B")

    fetcher.reviews = [
        {"review_id": "a1", "rating": 5, "snippet": "Review for A"}
    ]
    assert start(client, target_a["id"]).status_code == 200

    fetcher.reviews = [
        {"review_id": "b1", "rating": 2, "snippet": "Review for B"}
    ]
    assert start(client, target_b["id"]).status_code == 200

    def get_reviews(target_id):
        response = client.get(
            f"/api/targets/{target_id}/reviews",
            headers=headers(),
        )
        assert response.status_code == 200
        return response.json()

    reviews_a = get_reviews(target_a["id"])
    reviews_b = get_reviews(target_b["id"])
    reviews_a_again = get_reviews(target_a["id"])

    assert [r["text"] for r in reviews_a] == ["Review for A"]
    assert [r["text"] for r in reviews_b] == ["Review for B"]
    assert reviews_a_again == reviews_a
