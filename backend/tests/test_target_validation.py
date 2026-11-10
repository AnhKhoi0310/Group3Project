"""AnalysisTarget input validation (S1-016). No database required."""

import pytest
from pydantic import ValidationError

from app.schemas import URL_NO_PLACE, URL_WRONG_SITE, TargetCreate

DATA_ID_URL = "https://www.google.com/maps/place/Example+Cafe/data=!1s0x1:0x2"
PLACE_ID_URL = (
    "https://www.google.com/maps/search/?api=1&query=Cafe&query_place_id=ChIJExample1"
)


def first_error(**payload) -> str:
    with pytest.raises(ValidationError) as caught:
        TargetCreate(**payload)
    return caught.value.errors()[0]["msg"]


@pytest.mark.parametrize("url", [DATA_ID_URL, PLACE_ID_URL])
def test_valid_input_is_accepted_and_trimmed(url):
    target = TargetCreate(name="  Example Cafe  ", source_url=f"  {url}  ")

    assert target.name == "Example Cafe"
    assert target.source_url == url


@pytest.mark.parametrize("name", ["", "   ", "x" * 256])
def test_bad_name_is_rejected(name):
    with pytest.raises(ValidationError) as caught:
        TargetCreate(name=name, source_url=DATA_ID_URL)

    assert caught.value.errors()[0]["loc"] == ("name",)


@pytest.mark.parametrize("url", ["", "   "])
def test_missing_source_is_rejected(url):
    with pytest.raises(ValidationError) as caught:
        TargetCreate(name="Cafe", source_url=url)

    assert caught.value.errors()[0]["loc"] == ("source_url",)


@pytest.mark.parametrize(
    "url",
    [
        "not a url",
        "www.google.com/maps/place/x/data=!1s0x1:0x2",
        "http://www.google.com/maps/place/x/data=!1s0x1:0x2",
        "https://",
    ],
)
def test_malformed_url_is_rejected(url):
    assert "valid web address" in first_error(name="Cafe", source_url=url)


@pytest.mark.parametrize(
    "url",
    [
        "https://example.com/maps/place/x/data=!1s0x1:0x2",
        "https://google.com.evil.example/maps/place/x/data=!1s0x1:0x2",
        "https://www.google.com/search?q=cafe",
    ],
)
def test_other_sites_are_rejected(url):
    assert first_error(name="Cafe", source_url=url).endswith(URL_WRONG_SITE)


@pytest.mark.parametrize(
    "url",
    [
        "https://www.google.com/maps/place/Example+Cafe",
        "https://www.google.com/maps/search/?api=1&query=Cafe",
        "https://www.google.com/maps/place/x/data=!1snot-an-id!",
    ],
)
def test_maps_link_without_a_place_id_is_rejected(url):
    assert first_error(name="Cafe", source_url=url).endswith(URL_NO_PLACE)


def test_client_supplied_owner_and_platform_are_dropped():
    target = TargetCreate(
        name="Cafe", source_url=DATA_ID_URL, owner_id=9, user_id=9, platform="yelp"
    )

    assert not hasattr(target, "owner_id")
    assert not hasattr(target, "platform")
