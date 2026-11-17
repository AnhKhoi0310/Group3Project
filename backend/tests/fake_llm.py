from dataclasses import dataclass, field


@dataclass
class FakeLLM:
    """Deterministic replacement for the real language model boundary."""

    response: str = "This is a deterministic test answer."
    requests: list[dict[str, str]] = field(default_factory=list)

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Record the request and return a controlled response."""
        self.requests.append(
            {
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
            }
        )
        return self.response

    @property
    def call_count(self) -> int:
        return len(self.requests)

    @property
    def last_request(self) -> dict[str, str] | None:
        if not self.requests:
            return None
        return self.requests[-1]
