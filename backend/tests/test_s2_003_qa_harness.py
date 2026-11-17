import pytest
from fake_llm import FakeLLM

from app.models import AnalysisTarget, IngestionAttempt, Review, User
from app.services.qa import (
    INSUFFICIENT_EVIDENCE_ANSWER,
    TargetNotFoundError,
    answer_question,
)


def create_user(db, firebase_uid: str) -> User:
    user = User(
        firebase_uid=firebase_uid,
        email=f"{firebase_uid}@example.com",
    )
    db.add(user)
    db.flush()
    return user


def create_target(db, owner_id: int, name: str) -> AnalysisTarget:
    target = AnalysisTarget(
        owner_id=owner_id,
        name=name,
        platform="google_maps",
        source_url=("https://www.google.com/maps/place/Test/data=!1s0x1:0x2"),
    )
    db.add(target)
    db.flush()
    return target


def create_successful_ingestion(db, target_id: int) -> IngestionAttempt:
    attempt = IngestionAttempt(
        target_id=target_id,
        status="succeeded",
        reviews_found=1,
        reviews_skipped=0,
    )
    db.add(attempt)
    db.flush()
    return attempt


def create_review(
    db,
    target_id: int,
    text: str,
    rating: float = 5,
) -> Review:
    review = Review(
        target_id=target_id,
        source_platform="google_maps",
        text=text,
        rating=rating,
    )
    db.add(review)
    db.flush()
    return review


def test_system_instructions_define_the_reviewlens_scope(db):
    user = create_user(db, "scope-test-user")
    target = create_target(db, user.id, "Northside Cafe")
    create_successful_ingestion(db, target.id)
    create_review(db, target.id, "The coffee was excellent.")

    llm = FakeLLM(response="Customers liked the coffee.")

    result = answer_question(
        session=db,
        owner_id=user.id,
        target_id=target.id,
        question="What did customers like?",
        llm=llm,
    )

    assert result.status == "answered"
    assert llm.call_count == 1

    system_prompt = llm.last_request["system_prompt"]

    assert "ReviewLens" in system_prompt
    assert "Northside Cafe" in system_prompt
    assert "google_maps" in system_prompt
    assert "only using the review evidence" in system_prompt
    assert "Do not use general world knowledge" in system_prompt
    assert "Never invent review content" in system_prompt
    assert "insufficient evidence" in system_prompt
    assert "Decline questions unrelated" in system_prompt
    assert "untrusted data" in system_prompt


def test_only_reviews_from_the_active_target_enter_model_context(db):
    user = create_user(db, "same-owner-user")

    target_a = create_target(db, user.id, "Target A")
    target_b = create_target(db, user.id, "Target B")

    create_successful_ingestion(db, target_a.id)
    create_successful_ingestion(db, target_b.id)

    create_review(
        db,
        target_a.id,
        "ACTIVE_TARGET_REVIEW_A",
        rating=5,
    )
    create_review(
        db,
        target_b.id,
        "WRONG_TARGET_REVIEW_B",
        rating=1,
    )

    llm = FakeLLM(response="The active target received positive feedback.")

    result = answer_question(
        session=db,
        owner_id=user.id,
        target_id=target_a.id,
        question="What do customers say?",
        llm=llm,
    )

    user_prompt = llm.last_request["user_prompt"]

    assert result.target_id == target_a.id
    assert result.reviews_used == 1
    assert "ACTIVE_TARGET_REVIEW_A" in user_prompt
    assert "WRONG_TARGET_REVIEW_B" not in user_prompt


def test_switching_targets_builds_fresh_context(db):
    user = create_user(db, "target-switch-user")

    target_a = create_target(db, user.id, "Target A")
    target_b = create_target(db, user.id, "Target B")

    create_successful_ingestion(db, target_a.id)
    create_successful_ingestion(db, target_b.id)

    create_review(db, target_a.id, "ONLY_REVIEW_FOR_TARGET_A")
    create_review(db, target_b.id, "ONLY_REVIEW_FOR_TARGET_B")

    llm = FakeLLM()

    result_a = answer_question(
        session=db,
        owner_id=user.id,
        target_id=target_a.id,
        question="Summarize the reviews.",
        llm=llm,
    )
    prompt_a = llm.last_request["user_prompt"]

    result_b = answer_question(
        session=db,
        owner_id=user.id,
        target_id=target_b.id,
        question="Summarize the reviews.",
        llm=llm,
    )
    prompt_b = llm.last_request["user_prompt"]

    assert result_a.target_id == target_a.id
    assert result_b.target_id == target_b.id

    assert "ONLY_REVIEW_FOR_TARGET_A" in prompt_a
    assert "ONLY_REVIEW_FOR_TARGET_B" not in prompt_a

    assert "ONLY_REVIEW_FOR_TARGET_B" in prompt_b
    assert "ONLY_REVIEW_FOR_TARGET_A" not in prompt_b

    assert llm.call_count == 2


def test_reviews_from_another_users_target_are_never_sent_to_the_model(db):
    owner_a = create_user(db, "owner-a")
    owner_b = create_user(db, "owner-b")

    private_target = create_target(
        db,
        owner_b.id,
        "Private Target",
    )
    create_successful_ingestion(db, private_target.id)
    create_review(
        db,
        private_target.id,
        "PRIVATE_CROSS_USER_REVIEW",
    )

    llm = FakeLLM()

    with pytest.raises(TargetNotFoundError):
        answer_question(
            session=db,
            owner_id=owner_a.id,
            target_id=private_target.id,
            question="What do customers say?",
            llm=llm,
        )

    assert llm.call_count == 0
    assert llm.requests == []


def test_target_without_reviews_does_not_call_the_model(db):
    user = create_user(db, "empty-target-user")
    target = create_target(db, user.id, "Empty Target")
    create_successful_ingestion(db, target.id)

    llm = FakeLLM()

    result = answer_question(
        session=db,
        owner_id=user.id,
        target_id=target.id,
        question="What do customers think?",
        llm=llm,
    )

    assert result.status == "insufficient_evidence"
    assert result.answer == INSUFFICIENT_EVIDENCE_ANSWER
    assert result.reviews_used == 0
    assert llm.call_count == 0


def test_reviews_without_successful_ingestion_do_not_produce_a_normal_answer(db):
    user = create_user(db, "un-ingested-target-user")
    target = create_target(db, user.id, "Not Ingested Target")

    create_review(
        db,
        target.id,
        "REVIEW_WITHOUT_SUCCESSFUL_INGESTION",
    )

    llm = FakeLLM()

    result = answer_question(
        session=db,
        owner_id=user.id,
        target_id=target.id,
        question="What do customers think?",
        llm=llm,
    )

    assert result.status == "insufficient_evidence"
    assert result.answer == INSUFFICIENT_EVIDENCE_ANSWER
    assert result.reviews_used == 0
    assert llm.call_count == 0


def test_controlled_model_response_is_returned_to_the_application(db):
    user = create_user(db, "controlled-response-user")
    target = create_target(db, user.id, "Controlled Response Cafe")

    create_successful_ingestion(db, target.id)
    create_review(db, target.id, "Customers praised the service.")

    expected_response = "Customers praised the service in the supplied reviews."
    llm = FakeLLM(response=expected_response)

    result = answer_question(
        session=db,
        owner_id=user.id,
        target_id=target.id,
        question="What did customers praise?",
        llm=llm,
    )

    assert result.status == "answered"
    assert result.answer == expected_response
    assert result.target_id == target.id
    assert result.reviews_used == 1
    assert llm.call_count == 1


def test_empty_question_is_rejected_without_calling_the_model(db):
    user = create_user(db, "empty-question-user")
    target = create_target(db, user.id, "Question Validation Cafe")

    llm = FakeLLM()

    with pytest.raises(ValueError, match="A question is required"):
        answer_question(
            session=db,
            owner_id=user.id,
            target_id=target.id,
            question="   ",
            llm=llm,
        )

    assert llm.call_count == 0
