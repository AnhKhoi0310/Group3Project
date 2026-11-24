# Sprint 2 extra: reviewer avatars and customer photos (tag: Photos).
# Search a story ID (for example S2-016) to find its tests. Map: docs/testing.md
"""Reviewer avatars and customer photos collected with reviews."""

import pytest
import test_s1_022_s1_023 as s1_helpers
from fake_llm import FakeLLM, structured_reply
from sqlalchemy import select

from app.main import app
from app.models import Review
from app.routers.questions import get_llm_client
from app.services.normalizer import MAX_REVIEW_IMAGES, image_url, normalize_review

AVATAR = "https://lh3.googleusercontent.com/a-/avatar=s120"
PHOTO_1 = "https://lh3.googleusercontent.com/grass-cs/photo-1=w600"
PHOTO_2 = "https://lh5.ggpht.com/photo-2=w600"


def record(review_id="r1", text="Great slice.", images=(PHOTO_1, PHOTO_2)):
    return {
        "review_id": review_id,
        "rating": 5,
        "snippet": text,
        "user": {"name": "Ana", "thumbnail": AVATAR},
        "images": list(images),
    }


# Which image URLs are accepted


# Photos: Google image links are kept
@pytest.mark.parametrize("url", [AVATAR, PHOTO_2, {"thumbnail": PHOTO_1}])
def test_google_image_urls_are_kept(url):
    assert image_url(url) is not None


# Photos: unsafe or unusable image links are dropped
@pytest.mark.parametrize(
    "url",
    [
        "http://lh3.googleusercontent.com/insecure",
        "https://evil.example/pixel.png",
        "https://googleusercontent.com.evil.example/x",
        "javascript:alert(1)",
        "https://lh3.googleusercontent.com/" + "x" * 1100,
        "",
        None,
        42,
        {"other": PHOTO_1},
    ],
)
def test_unsafe_or_unusable_image_urls_are_dropped(url):
    assert image_url(url) is None


# Photos: the normalizer keeps the avatar and unique photos
def test_normalized_review_carries_avatar_and_deduplicated_photos():
    raw = record(images=[PHOTO_1, PHOTO_1, "https://evil.example/x", PHOTO_2])

    review = normalize_review(raw, "place-1")

    assert review["avatar_url"] == AVATAR
    assert review["image_urls"] == [PHOTO_1, PHOTO_2]


# Photos: at most 6 photos per review
def test_photos_are_capped():
    photos = [f"https://lh3.googleusercontent.com/p{i}" for i in range(10)]

    review = normalize_review(record(images=photos), "place-1")

    assert review["image_urls"] == photos[:MAX_REVIEW_IMAGES]


# Photos: a review with no media gets empty values
def test_review_without_media_gets_empty_values():
    review = normalize_review({"rating": 4, "snippet": "Fine."}, "place-1")

    assert (review["avatar_url"], review["image_urls"]) == (None, [])


# Through ingestion, storage and the API


# Photos: collected photos are saved and returned by the API
def test_collected_photos_are_saved_and_listed(client, fetcher):
    target = s1_helpers.create_target(client)
    fetcher.reviews = [record()]

    assert s1_helpers.start(client, target["id"]).status_code == 200
    reviews = client.get(
        f"/api/targets/{target['id']}/reviews", headers=s1_helpers.headers()
    ).json()

    assert reviews[0]["reviewer_avatar_url"] == AVATAR
    assert reviews[0]["image_urls"] == [PHOTO_1, PHOTO_2]


# Photos: a review without photos returns an empty list
def test_review_without_photos_lists_an_empty_photo_list(client, fetcher):
    target = s1_helpers.create_target(client)
    fetcher.reviews = [{"review_id": "r1", "rating": 3, "snippet": "Okay."}]

    s1_helpers.start(client, target["id"])
    review = client.get(
        f"/api/targets/{target['id']}/reviews", headers=s1_helpers.headers()
    ).json()[0]

    assert (review["reviewer_avatar_url"], review["image_urls"]) == (None, [])


# Photos: re-collecting adds photos without changing text or rating
def test_recollecting_fills_in_photos_without_changing_the_review(
    client, fetcher, session_factory
):
    target = s1_helpers.create_target(client)
    fetcher.reviews = [{"review_id": "r1", "rating": 4, "snippet": "Original text."}]
    s1_helpers.start(client, target["id"])

    fetcher.reviews = [record(review_id="r1", text="Edited text upstream.")]
    second = s1_helpers.start(client, target["id"]).json()

    with session_factory() as session:
        rows = session.scalars(select(Review).where(Review.target_id == target["id"]))
        rows = list(rows)
    assert len(rows) == 1
    assert second["reviews_found"] == 1  # found again, but not saved twice
    assert (rows[0].text, rows[0].rating) == ("Original text.", 4)
    assert rows[0].reviewer_avatar_url == AVATAR
    assert rows[0].image_urls == [PHOTO_1, PHOTO_2]


# Photos: existing photos are never replaced
def test_existing_photos_are_not_replaced(client, fetcher, session_factory):
    target = s1_helpers.create_target(client)
    fetcher.reviews = [record(images=[PHOTO_1])]
    s1_helpers.start(client, target["id"])

    fetcher.reviews = [record(images=[PHOTO_2])]
    s1_helpers.start(client, target["id"])

    with session_factory() as session:
        row = session.scalars(
            select(Review).where(Review.target_id == target["id"])
        ).one()
    assert row.image_urls == [PHOTO_1]


# Photos: cited reviews include photos, which never reach the model
def test_cited_reviews_in_answers_include_their_photos(client, fetcher):
    target = s1_helpers.create_target(client)
    fetcher.reviews = [record()]
    s1_helpers.start(client, target["id"])
    review_id = client.get(
        f"/api/targets/{target['id']}/reviews", headers=s1_helpers.headers()
    ).json()[0]["id"]
    llm = FakeLLM(response=structured_reply(ids=[review_id]))
    app.dependency_overrides[get_llm_client] = lambda: llm

    answer = client.post(
        f"/api/targets/{target['id']}/questions",
        json={"question": "What do people like?"},
        headers=s1_helpers.headers(),
    ).json()

    assert answer["evidence"][0]["image_urls"] == [PHOTO_1, PHOTO_2]
    assert answer["evidence"][0]["reviewer_avatar_url"] == AVATAR
    assert PHOTO_1 not in llm.last_request["user_prompt"]  # photos aren't sent
