"""The Claude adapter, tested against a fake SDK client. No network calls."""

from types import SimpleNamespace

import anthropic
import httpx2
import pytest

import app.routers.questions as questions
from app.adapters.llm import (
    ANSWER_SCHEMA,
    DEFAULT_MODEL,
    FALLBACK_BETA,
    ClaudeClient,
    LLMError,
)
from app.config import load_settings
from app.errors import ApiError

REQUEST = httpx2.Request("POST", "https://api.anthropic.com/v1/messages")


def reply(text='{"disposition": "answered"}', stop_reason="end_turn"):
    blocks = [SimpleNamespace(type="thinking", thinking="")]
    if text is not None:
        blocks.append(SimpleNamespace(type="text", text=text))
    return SimpleNamespace(stop_reason=stop_reason, content=blocks)


class FakeAnthropic:
    def __init__(self, response=None, error=None):
        self.calls = []
        self._response = response or reply()
        self._error = error
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        self.calls.append(kwargs)
        if self._error is not None:
            raise self._error
        return self._response


def status_error(cls, code):
    return cls(
        "provider detail", response=httpx2.Response(code, request=REQUEST), body=None
    )


def test_request_sends_prompts_schema_and_fallback():
    fake = FakeAnthropic()

    ClaudeClient(api_key="k", client=fake).generate("SYSTEM", "USER")

    call = fake.calls[0]
    assert call["model"] == DEFAULT_MODEL
    assert call["system"] == "SYSTEM"
    assert call["messages"] == [{"role": "user", "content": "USER"}]
    assert call["output_config"]["format"] == {
        "type": "json_schema",
        "schema": ANSWER_SCHEMA,
    }
    assert call["output_config"]["effort"] == "medium"
    assert call["betas"] == [FALLBACK_BETA]
    assert call["fallbacks"] == "default"


def test_configured_model_is_used():
    fake = FakeAnthropic()

    ClaudeClient(api_key="k", model="claude-opus-5-5", client=fake).generate("s", "u")

    assert fake.calls[0]["model"] == "claude-opus-5-5"


def test_reply_text_is_returned_without_thinking_blocks():
    fake = FakeAnthropic(response=reply('{"answer": "ok"}'))

    assert ClaudeClient(api_key="k", client=fake).generate("s", "u") == (
        '{"answer": "ok"}'
    )


@pytest.mark.parametrize(
    ("error", "category"),
    [
        (anthropic.APITimeoutError(request=REQUEST), "timeout"),
        (anthropic.APIConnectionError(request=REQUEST), "unavailable"),
        (status_error(anthropic.RateLimitError, 429), "rate_limited"),
        (status_error(anthropic.AuthenticationError, 401), "misconfigured"),
        (status_error(anthropic.PermissionDeniedError, 403), "misconfigured"),
        (status_error(anthropic.InternalServerError, 500), "unavailable"),
        (status_error(anthropic.BadRequestError, 400), "unexpected"),
    ],
)
def test_provider_errors_map_to_distinct_categories(error, category):
    client = ClaudeClient(api_key="k", client=FakeAnthropic(error=error))

    with pytest.raises(LLMError) as caught:
        client.generate("s", "u")

    assert caught.value.category == category
    assert "provider detail" not in str(caught.value)


@pytest.mark.parametrize(
    ("response", "category"),
    [
        (reply(None, stop_reason="refusal"), "refused"),
        (reply("{", stop_reason="max_tokens"), "unexpected"),
        (reply("   "), "unexpected"),
        (reply(None), "unexpected"),
    ],
)
def test_unusable_replies_are_reported(response, category):
    client = ClaudeClient(api_key="k", client=FakeAnthropic(response=response))

    with pytest.raises(LLMError) as caught:
        client.generate("s", "u")

    assert caught.value.category == category


def test_client_can_be_built_from_an_api_key_without_calling_the_provider():
    assert ClaudeClient(api_key="test-key")._client.api_key == "test-key"


def settings(**overrides):
    return load_settings(
        _env_file=None,
        database_url="mysql+pymysql://u:p@localhost/db",
        firebase_project_id="p",
        firebase_credentials_path="k.json",
        review_provider_api_key="r",
        **overrides,
    )


def test_missing_api_key_makes_qa_unavailable(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr(questions, "get_settings", lambda: settings())

    with pytest.raises(ApiError) as caught:
        questions.get_llm_client()

    assert (caught.value.status_code, caught.value.code) == (503, "qa_unavailable")


def test_configured_api_key_builds_the_claude_client(monkeypatch):
    monkeypatch.setattr(
        questions,
        "get_settings",
        lambda: settings(anthropic_api_key="key-1", llm_model="claude-sonnet-5-5"),
    )

    client = questions.get_llm_client()

    assert isinstance(client, ClaudeClient)
    assert client is questions.get_llm_client()  # reused, not rebuilt per request
