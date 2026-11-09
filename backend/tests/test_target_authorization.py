from fastapi import status
from fastapi.testclient import TestClient


def test_user_cannot_access_other_users_target(
    client: TestClient, auth_headers_user1: dict, target_owned_by_user2: int
) -> None:
    """Ensure user1 receives a 404 when requesting user2's target."""
    response = client.get(
        f"/targets/{target_owned_by_user2}",
        headers=auth_headers_user1,
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_user_list_only_shows_owned_targets(
    client: TestClient,
    auth_headers_user1: dict,
    target_owned_by_user2: int,
) -> None:
    """Ensure listing targets excludes items owned by another user."""
    response = client.get("/targets/", headers=auth_headers_user1)
    assert response.status_code == status.HTTP_200_OK
    targets = response.json()
    assert isinstance(targets, list)
    assert all(target["id"] != target_owned_by_user2 for target in targets)
