
from fake_llm import FakeLLM


def test_fake_llm_returns_controlled_response():
    llm = FakeLLM(response="Customers appreciate the service.")

    result = llm.generate(
        system_prompt="Answer questions using customer reviews.",
        user_prompt="What do customers like?",
    )

    assert result == "Customers appreciate the service."
    assert llm.call_count == 1


def test_fake_llm_records_system_instructions():
    llm = FakeLLM()

    llm.generate(
        system_prompt="Use only the supplied reviews.",
        user_prompt="Summarize the reviews.",
    )

    assert llm.last_request["system_prompt"] == (
        "Use only the supplied reviews."
    )


def test_fake_llm_records_review_context():
    llm = FakeLLM()

    llm.generate(
        system_prompt="Answer based on reviews.",
        user_prompt="Reviews: Excellent food, Slow delivery",
    )

    assert "Excellent food" in llm.last_request["user_prompt"]
    assert "Slow delivery" in llm.last_request["user_prompt"]


def test_fake_llm_does_not_make_external_requests():
    llm = FakeLLM(response="Mock answer")

    for _ in range(5):
        assert llm.generate("System", "Question") == "Mock answer"

    assert llm.call_count == 5
