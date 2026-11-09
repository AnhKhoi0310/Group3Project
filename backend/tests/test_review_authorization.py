from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.adapters.identity import VerifiedIdentity
from app.auth import get_token_verifier, get_verified_identity
from app.main import app
from app.models.models import AnalysisTarget, Review
from app.repositories.users import get_or_create_user


class StaticVerifier:
    def __init__(self, identity: VerifiedIdentity):
        self.identity = identity

    def verify(self, token: str):
        return self.identity

    def revoke(self, uid: str):
        pass


def setup_auth(user_identity: VerifiedIdentity, db: Session) -> dict:
    user = get_or_create_user(db, user_identity)
    db.commit()
    app.dependency_overrides[get_verified_identity] = lambda: user_identity
    app.dependency_overrides[get_token_verifier] = lambda: StaticVerifier(
        user_identity
    )
    return {
        "Authorization": "Bearer token",
        "X-User-Id": user_identity.uid,
        "X-Owner-Id": str(user.id),
    }


def test_user_cannot_read_other_users_target_reviews(client: TestClient, db: Session):
    """Verify User B receives a 404 when requesting reviews for User A's target."""
    user1_id = VerifiedIdentity(uid="user1-uid", email="u1@example.com")
    user2_id = VerifiedIdentity(uid="user2-uid", email="u2@example.com")

    user1 = get_or_create_user(db, user1_id)
    target = AnalysisTarget(owner_id=user1.id, name="User 1 Target")
    db.add(target)
    db.commit()

    review = Review(target_id=target.id, text="Great service", rating=5)
    db.add(review)
    db.commit()

    auth_headers_user2 = setup_auth(user2_id, db)

    response = client.get(
        f"/api/targets/{target.id}/reviews",
        headers=auth_headers_user2,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    app.dependency_overrides.clear()


def test_user_cannot_submit_ingestion_against_other_users_target(
    client: TestClient, db: Session
):
    """Verify User B cannot trigger ingestion against User A's target."""
    user1_id = VerifiedIdentity(uid="user1-uid", email="u1@example.com")
    user2_id = VerifiedIdentity(uid="user2-uid", email="u2@example.com")

    user1 = get_or_create_user(db, user1_id)
    target = AnalysisTarget(owner_id=user1.id, name="User 1 Target")
    db.add(target)
    db.commit()

    auth_headers_user2 = setup_auth(user2_id, db)

    response = client.post(
        f"/api/targets/{target.id}/ingest",
        headers=auth_headers_user2,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    app.dependency_overrides.clear()


def test_user_cannot_create_review_under_other_users_target(
    client: TestClient, db: Session
):
    """Verify User B cannot create a review under User A's target."""
    user1_id = VerifiedIdentity(uid="user1-uid", email="u1@example.com")
    user2_id = VerifiedIdentity(uid="user2-uid", email="u2@example.com")

    user1 = get_or_create_user(db, user1_id)
    target = AnalysisTarget(owner_id=user1.id, name="User 1 Target")
    db.add(target)
    db.commit()

    auth_headers_user2 = setup_auth(user2_id, db)

    response = client.post(
        f"/api/targets/{target.id}/reviews",
        json={"text": "Forged review", "rating": 1},
        headers=auth_headers_user2,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    app.dependency_overrides.clear()
