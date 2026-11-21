
"""Review Q&A through the HTTP API (S2-008 to S2-012), on real MySQL.

The model is the deterministic FakeLLM from fake_llm.py, so these tests check
what ReviewLens sends to the model and how it handles each kind of reply,
never the wording of a live model.
"""

import json

import pytest
from fake_llm import FailingLLM, FakeLLM, structured_reply
from fastapi.testclient import TestClient
from test_s1_022_s1_023 import FakeVerifier

import app.main as main_module
from app.auth import get_token_verifier
from app.config import load_settings
from app.db import get_session
from app.main import app
from app.models import AnalysisTarget, IngestionAttempt, Review
from app.routers.questions import get_llm_client
from app.services.qa import MAX_CONTEXT_REVIEWS

SOURCE_URL = "https://www.google.com/maps/place/Test/data=!1s0x1:0x2"


def headers(token="token-a"):
    return {"Authorization": f"Bearer {token}"}


model_reply = structured_reply


@pytest.fixture
def llm():
    return FakeLLM(response=model_reply())


@pytest.fixture
def client(db, session_factory, llm, monkeypatch):
    def session_override():
        with session_factory() as session:
            yield session

    verifier = FakeVerifier()
    monkeypatch.setattr(
        main_module,
        "get_settings",
        lambda: load_settings(
            _env_file=None,
            database_url="mysql+pymysql://unused/unused",
            firebase_project_id="test-project",
            firebase_credentials_path="unused.json",
            review_provider_api_key="test-api-key",
        ),
    )
    monkeypatch.setattr(main_module, "get_token_verifier", lambda: verifier)
    previous = app.dependency_overrides.copy()
    app.dependency_overrides[get_token_verifier] = lambda: verifier
    app.dependency_overrides[get_session] = session_override
    app.dependency_overrides[get_llm_client] = lambda: llm
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)


def create_target(client, name="Luigi's Trattoria", token="token-a"):
    response = client.post(
        "/api/targets",
        json={"name": name, "source_url": SOURCE_URL},
        headers=headers(token),
    )
    assert response.status_code == 201, response.text
    return response.json()


def add_reviews(session_factory, target_id, texts, rating=5, ingested=True):
    """Persist reviews (and a successful run) for a target; return their IDs."""
    with session_factory() as session:
        rows = [
            Review(
                target_id=target_id,
                source_platform="google_maps",
                text=text,
                rating=rating,
            )
            for text in texts
        ]
        session.add_all(rows)
        if ingested:
            session.add(
                IngestionAttempt(
                    target_id=target_id,
                    status="succeeded",
                    reviews_found=len(rows),
                    reviews_skipped=0,
                )
            )
        session.commit()
        return [row.id for row in rows]


def ask(client, target_id, question="What do customers like?", token="token-a"):
    return client.post(
        f"/api/targets/{target_id}/questions",
        json={"question": question},
        headers=headers(token),
    )


def test_answer_is_returned_with_the_reviews_it_cites(client, llm, session_factory):
    target = create_target(client)
    ids = add_reviews(
        session_factory, target["id"], ["The pasta is superb.", "Slow service."]
    )
    llm.response = model_reply(ids=[ids[0]])

    response = ask(client, target["id"])

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "answered"
    assert body["answer"] == "Customers praise the pasta."
    assert body["target_name"] == "Luigi's Trattoria"
    assert (body["reviews_used"], body["reviews_total"]) == (2, 2)
    assert [e["text"] for e in body["evidence"]] == ["The pasta is superb."]
    assert llm.call_count == 1
    assert "Luigi's Trattoria" in llm.last_request["system_prompt"]
    assert "What do customers like?" in llm.last_request["user_prompt"]


def test_question_about_missing_evidence_is_reported_as_insufficient(
    client, llm, session_factory
):
    """S2-012: the reviews cover food and service; nothing mentions parking."""
    target = create_target(client)
    add_reviews(
        session_factory,
        target["id"],
        ["The lasagna was rich and hot.", "Our waiter was friendly and quick."],
    )
    llm.response = model_reply(
        "insufficient_evidence",
        "The reviews discuss food and service but say nothing about parking.",
    )

    response = ask(client, target["id"], "Do customers think the parking lot is safe?")

    body = response.json()
    assert response.status_code == 200
    assert body["status"] == "insufficient_evidence"
    assert body["evidence"] == []
    assert body["reviews_used"] == 2  # the model did see the dataset
    supplied = llm.last_request["user_prompt"].split("Review evidence", 1)[1]
    assert "parking" not in supplied.lower()
    system_prompt = llm.last_request["system_prompt"]
    assert "absent from the reviews" in system_prompt
    assert "insufficient_evidence" in system_prompt


def test_declined_question_never_shows_evidence(client, llm, session_factory):
    target = create_target(client)
    ids = add_reviews(session_factory, target["id"], ["Great tiramisu."])
    llm.response = model_reply("declined", "I can only discuss these reviews.", ids)

    body = ask(client, target["id"], "Who won the World Cup?").json()

    assert body["status"] == "declined"
    assert body["evidence"] == []


def test_cited_ids_outside_the_supplied_reviews_are_dropped(
    client, llm, session_factory
):
    mine = create_target(client)
    other = create_target(client, "Other User's Cafe", token="token-b")
    my_ids = add_reviews(session_factory, mine["id"], ["Lovely terrace."])
    other_ids = add_reviews(session_factory, other["id"], ["SECRET-PHRASE-B"])
    llm.response = model_reply(ids=[other_ids[0], my_ids[0], 999999, "x"])

    body = ask(client, mine["id"]).json()

    assert [e["id"] for e in body["evidence"]] == my_ids
    assert "SECRET-PHRASE-B" not in json.dumps(body)
    assert "SECRET-PHRASE-B" not in llm.last_request["user_prompt"]


def test_another_users_target_returns_404_without_calling_the_model(
    client, llm, session_factory
):
    other = create_target(client, "User B Diner", token="token-b")
    add_reviews(session_factory, other["id"], ["SECRET-PHRASE-B"])

    response = ask(client, other["id"], token="token-a")

    assert response.status_code == 404
    assert response.json()["code"] == "target_not_found"
    assert llm.call_count == 0


def test_unknown_target_looks_the_same_as_someone_elses(client, llm):
    response = ask(client, 987654321)

    assert response.status_code == 404
    assert response.json()["code"] == "target_not_found"


@pytest.mark.parametrize("question", ["", "   ", "x" * 1001])
def test_blank_or_huge_question_is_rejected_before_the_model(client, llm, question):
    target = create_target(client)

    response = ask(client, target["id"], question)

    assert response.status_code == 422
    assert "question" in response.json()["fieldErrors"]
    assert llm.call_count == 0


def test_target_without_reviews_does_not_reach_the_model(client, llm):
    target = create_target(client)

    body = ask(client, target["id"]).json()

    assert body["status"] == "insufficient_evidence"
    assert body["reviews_used"] == 0
    assert llm.call_count == 0


def test_context_is_capped_at_the_most_recent_reviews(client, llm, session_factory):
    target = create_target(client)
    texts = [f"review-number-{i:03d}" for i in range(MAX_CONTEXT_REVIEWS + 5)]
    add_reviews(session_factory, target["id"], texts)

    body = ask(client, target["id"]).json()

    assert body["reviews_used"] == MAX_CONTEXT_REVIEWS
    assert body["reviews_total"] == MAX_CONTEXT_REVIEWS + 5
    sent = llm.last_request["user_prompt"]
    assert "review-number-204" in sent  # newest kept
    assert "review-number-000" not in sent  # oldest left out


def test_qa_and_summary_describe_the_same_dataset(client, llm, session_factory):
    """S2-008: the summary and Q&A read the same persisted reviews."""
    target = create_target(client)
    add_reviews(session_factory, target["id"], ["One", "Two", "Three"], rating=4)

    summary = client.get(f"/api/targets/{target['id']}/summary", headers=headers())
    answer = ask(client, target["id"]).json()

    assert summary.json()["review_count"] == answer["reviews_total"] == 3

    add_reviews(session_factory, target["id"], ["Four"], rating=2)
    summary = client.get(f"/api/targets/{target['id']}/summary", headers=headers())
    answer = ask(client, target["id"]).json()

    assert summary.json()["review_count"] == answer["reviews_total"] == 4
    assert summary.json()["average_rating"] == 3.5


def test_switching_targets_sends_only_the_new_targets_reviews(
    client, llm, session_factory
):
    first = create_target(client, "Battery Shop")
    second = create_target(client, "Service Desk")
    add_reviews(session_factory, first["id"], ["battery life is amazing"])
    add_reviews(session_factory, second["id"], ["customer service was rude"])

    ask(client, first["id"])
    ask(client, second["id"])

    latest = llm.last_request
    assert "customer service was rude" in latest["user_prompt"]
    assert "battery life" not in latest["user_prompt"]
    assert "Service Desk" in latest["system_prompt"]
    assert "Battery Shop" not in latest["system_prompt"]


def test_plain_text_model_reply_is_shown_as_an_answer(client, llm, session_factory):
    target = create_target(client)
    add_reviews(session_factory, target["id"], ["Nice."])
    llm.response = "Reviewers liked it."

    body = ask(client, target["id"]).json()

    assert (body["status"], body["answer"], body["evidence"]) == (
        "answered",
        "Reviewers liked it.",
        [],
    )


def test_model_refusal_becomes_a_clear_decline(client, session_factory):
    target = create_target(client)
    add_reviews(session_factory, target["id"], ["Nice."])
    app.dependency_overrides[get_llm_client] = lambda: FailingLLM(category="refused")

    response = ask(client, target["id"])

    assert response.status_code == 200
    assert response.json()["status"] == "declined"


@pytest.mark.parametrize(
    ("category", "status_code", "code"),
    [
        ("timeout", 504, "qa_timeout"),
        ("rate_limited", 429, "qa_busy"),
        ("unavailable", 503, "qa_unavailable"),
        ("misconfigured", 503, "qa_unavailable"),
        ("unexpected", 502, "qa_failed"),
    ],
)
def test_model_failures_return_distinct_friendly_errors(
    client, session_factory, category, status_code, code
):
    target = create_target(client)
    add_reviews(session_factory, target["id"], ["Nice."])
    app.dependency_overrides[get_llm_client] = lambda: FailingLLM(category=category)

    response = ask(client, target["id"])

    assert response.status_code == status_code
    assert response.json()["code"] == code
    assert category not in response.json()["message"]


def test_owner_fields_in_the_body_are_ignored(client, llm, session_factory):
    other = create_target(client, "User B Diner", token="token-b")
    add_reviews(session_factory, other["id"], ["SECRET-PHRASE-B"])
    mine = create_target(client)
    add_reviews(session_factory, mine["id"], ["Mine."])

    response = client.post(
        f"/api/targets/{mine['id']}/questions",
        json={"question": "Hi?", "owner_id": 1, "user_id": 1, "target_id": other["id"]},
        headers=headers(),
    )

    assert response.json()["target_id"] == mine["id"]
    assert "SECRET-PHRASE-B" not in llm.last_request["user_prompt"]
    with session_factory() as session:
        assert session.get(AnalysisTarget, other["id"]).name == "User B Diner"


def test_review_context_is_rebuilt_after_repeated_target_switches(
    client, llm, session_factory
):
    """S2-019: each question receives only the currently requested target's reviews."""
    first = create_target(client, "Battery Shop")
    second = create_target(client, "Service Desk")

    add_reviews(
        session_factory,
        first["id"],
        ["UNIQUE-BATTERY-TARGET-ALPHA"],
    )
    add_reviews(
        session_factory,
        second["id"],
        ["UNIQUE-SERVICE-TARGET-BETA"],
    )

    # First request: Target A.
    first_response = ask(client, first["id"])
    assert first_response.status_code == 200
    first_request = llm.requests[-1]

    # Second request: switch to Target B.
    second_response = ask(client, second["id"])
    assert second_response.status_code == 200
    second_request = llm.requests[-1]

    # Third request: switch back to Target A.
    third_response = ask(client, first["id"])
    assert third_response.status_code == 200
    third_request = llm.requests[-1]

    assert llm.call_count == 3

    # Target A's first request contains only Target A context.
    assert "UNIQUE-BATTERY-TARGET-ALPHA" in first_request["user_prompt"]
    assert "UNIQUE-SERVICE-TARGET-BETA" not in first_request["user_prompt"]
    assert "Battery Shop" in first_request["system_prompt"]

    # Target B's request contains only Target B context.
    assert "UNIQUE-SERVICE-TARGET-BETA" in second_request["user_prompt"]
    assert "UNIQUE-BATTERY-TARGET-ALPHA" not in second_request["user_prompt"]
    assert "Service Desk" in second_request["system_prompt"]
    assert "Battery Shop" not in second_request["system_prompt"]

    # Returning to Target A must not retain Target B's context.
    assert "UNIQUE-BATTERY-TARGET-ALPHA" in third_request["user_prompt"]
    assert "UNIQUE-SERVICE-TARGET-BETA" not in third_request["user_prompt"]
    assert "Battery Shop" in third_request["system_prompt"]
    assert "Service Desk" not in third_request["system_prompt"]
