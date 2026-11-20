import pytest

from app.models import AnalysisTarget, IngestionAttempt, Review, User
from app.services.qa import TargetNotFoundError, answer_question

USER_A_SECRET = "PURPLE PENGUIN GALAXY 8472"
USER_B_REVIEW = "Friendly staff and excellent coffee."


class CapturingLLM:
    """Capture exactly what the Q&A service sends to the model."""

    def __init__(self):
        self.calls = []

    def generate(self, system_prompt, user_prompt):
        self.calls.append(
            {
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
            }
        )
        return "Answer based on the supplied review context."


@pytest.fixture
def two_user_datasets(db):
    """Create two real users with separate targets and reviews."""
    user_a = User(firebase_uid="s2-016-user-a")
    user_b = User(firebase_uid="s2-016-user-b")

    db.add_all([user_a, user_b])
    db.flush()

    target_a = AnalysisTarget(
        owner_id=user_a.id,
        name="Private Business A",
        platform="google_maps",
        source_url="https://example.com/business-a",
    )
    target_b = AnalysisTarget(
        owner_id=user_b.id,
        name="Public Cafe B",
        platform="google_maps",
        source_url="https://example.com/business-b",
    )

    db.add_all([target_a, target_b])
    db.flush()

    db.add_all(
        [
            Review(
                target_id=target_a.id,
                source_platform="google_maps",
                text=USER_A_SECRET,
                rating=5.0,
            ),
            Review(
                target_id=target_b.id,
                source_platform="google_maps",
                text=USER_B_REVIEW,
                rating=4.0,
            ),
            IngestionAttempt(
                target_id=target_a.id,
                status="succeeded",
                reviews_found=1,
            ),
            IngestionAttempt(
                target_id=target_b.id,
                status="succeeded",
                reviews_found=1,
            ),
        ]
    )

    db.commit()

    return user_a, target_a, user_b, target_b


def test_user_b_cannot_access_user_a_target(db, two_user_datasets):
    user_a, target_a, user_b, target_b = two_user_datasets
    llm = CapturingLLM()

    with pytest.raises(TargetNotFoundError):
        answer_question(
            session=db,
            owner_id=user_b.id,
            target_id=target_a.id,
            question="Tell me everything about this business.",
            llm=llm,
        )

    assert llm.calls == []


def test_user_b_context_excludes_user_a_reviews(db, two_user_datasets):
    user_a, target_a, user_b, target_b = two_user_datasets
    llm = CapturingLLM()

    result = answer_question(
        session=db,
        owner_id=user_b.id,
        target_id=target_b.id,
        question="Summarize the customer feedback.",
        llm=llm,
    )

    assert len(llm.calls) == 1

    request = llm.calls[0]
    full_context = request["system_prompt"] + "\n" + request["user_prompt"]

    assert USER_B_REVIEW in full_context
    assert USER_A_SECRET not in full_context
    assert "Private Business A" not in full_context
    assert "Public Cafe B" in full_context

    assert result.target_id == target_b.id
    assert result.reviews_used == 1
    assert USER_A_SECRET not in result.answer


def test_user_a_context_excludes_user_b_reviews(db, two_user_datasets):
    user_a, target_a, user_b, target_b = two_user_datasets
    llm = CapturingLLM()

    result = answer_question(
        session=db,
        owner_id=user_a.id,
        target_id=target_a.id,
        question="Summarize the customer feedback.",
        llm=llm,
    )

    assert len(llm.calls) == 1

    request = llm.calls[0]
    full_context = request["system_prompt"] + "\n" + request["user_prompt"]

    assert USER_A_SECRET in full_context
    assert USER_B_REVIEW not in full_context
    assert "Public Cafe B" not in full_context

    assert result.target_id == target_a.id
    assert result.reviews_used == 1
