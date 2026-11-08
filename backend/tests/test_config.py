import pytest

from app.config import ConfigurationError, load_settings

SECRET = "super-secret-value"
VALID_ENV = {
    "DATABASE_URL": f"mysql+pymysql://user:{SECRET}@localhost:3306/reviewlens",
    "FIREBASE_PROJECT_ID": "reviewlens-test",
    "FIREBASE_CREDENTIALS_PATH": "secrets/firebase-admin.json",
    "REVIEW_PROVIDER_API_KEY": SECRET,
}


@pytest.fixture
def valid_env(monkeypatch):
    for name, value in VALID_ENV.items():
        monkeypatch.setenv(name, value)
    monkeypatch.delenv("INGESTION_MAX_REVIEWS", raising=False)


def load():
    return load_settings(_env_file=None)


def test_valid_configuration_loads_with_default_cap(valid_env):
    settings = load()

    assert settings.firebase_project_id == "reviewlens-test"
    assert settings.review_provider_api_key.get_secret_value() == SECRET
    assert settings.ingestion_max_reviews == 50


def test_ingestion_cap_is_configurable(valid_env, monkeypatch):
    monkeypatch.setenv("INGESTION_MAX_REVIEWS", "20")

    assert load().ingestion_max_reviews == 20


@pytest.mark.parametrize("name", sorted(VALID_ENV))
def test_missing_required_variable_is_named(valid_env, monkeypatch, name):
    monkeypatch.delenv(name)

    with pytest.raises(ConfigurationError, match=name):
        load()


@pytest.mark.parametrize("name", sorted(VALID_ENV))
def test_blank_required_variable_is_rejected(valid_env, monkeypatch, name):
    monkeypatch.setenv(name, "")

    with pytest.raises(ConfigurationError, match=name):
        load()


@pytest.mark.parametrize("value", ["0", "-1", "many"])
def test_invalid_ingestion_cap_is_rejected(valid_env, monkeypatch, value):
    monkeypatch.setenv("INGESTION_MAX_REVIEWS", value)

    with pytest.raises(ConfigurationError, match="INGESTION_MAX_REVIEWS"):
        load()


def test_error_does_not_expose_secret_values(valid_env, monkeypatch):
    monkeypatch.setenv("INGESTION_MAX_REVIEWS", SECRET)

    with pytest.raises(ConfigurationError) as caught:
        load()

    assert SECRET not in str(caught.value)
    assert caught.value.__cause__ is None
    assert caught.value.__suppress_context__ is True


def test_settings_repr_masks_secrets(valid_env):
    assert SECRET not in repr(load())
