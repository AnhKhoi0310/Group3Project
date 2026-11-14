
from dataclasses import dataclass, field


@dataclass
class FakeLLM:
    response: str = "This is a deterministic test answer."
    requests: list[dict] = field(default_factory=list)

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        self.requests.append({
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
        })
        return self.response

    @property
    def call_count(self) -> int:
        return len(self.requests)

    @property
    def last_request(self) -> dict | None:
        return self.requests[-1] if self.requests else None
