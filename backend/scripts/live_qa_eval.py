"""Run the scope-guard evaluation set against the live model.

This supplements the deterministic CI tests (S2-BR-031); CI never runs it.
It uses the real system prompt, the real Claude adapter and the app's own
reply checking, with a small fixed review set for "Northside Cafe" that matches
tests/scope_evaluation_cases.py. Each run makes one paid API call per case.

From backend/:   python scripts/live_qa_eval.py
Needs ANTHROPIC_API_KEY (and the other required settings) in backend/.env.
Exits with status 1 if any question gets the wrong kind of reply.
"""

import sys
import time
from pathlib import Path
from types import SimpleNamespace

BACKEND = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(BACKEND), str(BACKEND / "tests")]

from scope_evaluation_cases import (  # noqa: E402
    SCOPE_EVALUATION_CASES,
    evaluate_result,
)

from app.adapters.llm import ClaudeClient, LLMError  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.services.qa import (  # noqa: E402
    _build_system_prompt,
    _build_user_prompt,
    _parse_model_reply,
)

TARGET_NAME = "Northside Cafe"
PLATFORM = "google_maps"
REVIEWS = [
    (5, "Excellent coffee, easily the best espresso in the neighborhood."),
    (5, "Friendly staff who remember my order. The coffee is excellent."),
    (4, "Great cappuccino and pastries, but the wait was long on Saturday."),
    (2, "Slow service. We waited 25 minutes for two lattes."),
    (3, "Coffee is good, though the line is long and seating is limited."),
    (5, "Staff were friendly and the service was quick on a weekday morning."),
    (4, "Lovely atmosphere and excellent cold brew."),
    (1, "Very slow at lunch and my order was wrong."),
]


def main() -> int:
    settings = get_settings()
    if settings.anthropic_api_key is None:
        sys.exit("Set ANTHROPIC_API_KEY in backend/.env first.")
    client = ClaudeClient(
        settings.anthropic_api_key.get_secret_value(), settings.llm_model
    )
    reviews = [
        SimpleNamespace(
            id=index,
            rating=rating,
            text=text,
            reviewer_name=f"Reviewer {index}",
            review_date=None,
            source_platform=PLATFORM,
        )
        for index, (rating, text) in enumerate(REVIEWS, start=1)
    ]
    system_prompt = _build_system_prompt(TARGET_NAME, PLATFORM)
    print(f"Model: {settings.llm_model}. {len(SCOPE_EVALUATION_CASES)} questions.\n")

    failures = 0
    for case in SCOPE_EVALUATION_CASES:
        started = time.monotonic()
        try:
            raw = client.generate(
                system_prompt, _build_user_prompt(case["question"], reviews)
            )
            status, answer, evidence = _parse_model_reply(raw, reviews)
        except LLMError as exc:
            status, answer, evidence = f"error:{exc.category}", "", ()
        seconds = time.monotonic() - started

        problems = evaluate_result(case, status, answer, len(evidence))
        failures += bool(problems)

        mark = "FAIL" if problems else "ok  "
        cited = ",".join(str(review.id) for review in evidence) or "-"
        print(f"{mark} {case['id']} {status:<22} cited={cited:<8} {seconds:4.1f}s")
        print(f"     Q: {case['question']}")
        print(f"     A: {answer[:220]}")
        for problem in problems:
            print(f"     ! {problem}")

    total = len(SCOPE_EVALUATION_CASES)
    print(f"\n{total - failures}/{total} behaved as expected.")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
