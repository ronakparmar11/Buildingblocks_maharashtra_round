import json
import threading
import time
from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class LLMResponse:
    text: str
    json: dict[str, Any]
    tokens_in: int
    tokens_out: int
    model: str


class LLMClient(Protocol):
    def complete_json(
        self, prompt: str, temperature: float, sample_idx: int = 0
    ) -> LLMResponse: ...


class RateLimiter:
    def __init__(self, rpm_limit: int) -> None:
        self._interval = 60.0 / rpm_limit if rpm_limit > 0 else 0.0
        self._lock = threading.Lock()
        self._next_allowed = 0.0

    def wait(self) -> None:
        with self._lock:
            now = time.monotonic()
            delay = max(0.0, self._next_allowed - now)
            if delay:
                time.sleep(delay)
            self._next_allowed = max(now, self._next_allowed) + self._interval


def parse_json_object(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        stripped = "\n".join(lines).strip()

    parsed = json.loads(stripped)
    if not isinstance(parsed, dict):
        raise TypeError("LLM response must be a JSON object")
    return parsed


def is_retryable_error(error: BaseException) -> bool:
    status_code = getattr(error, "status_code", None)
    if status_code is None:
        response = getattr(error, "response", None)
        status_code = getattr(response, "status_code", None)
    return status_code == 429 or (
        isinstance(status_code, int) and 500 <= status_code < 600
    )
