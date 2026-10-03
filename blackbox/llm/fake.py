import json
from typing import Any

from blackbox.llm.base import LLMResponse


class FakeLLM:
    def __init__(
        self,
        script: dict[str, dict[str, Any]],
        model: str = "fake",
    ) -> None:
        self.script = script
        self.model = model
        self.calls = 0

    def complete_json(
        self, prompt: str, temperature: float, sample_idx: int = 0
    ) -> LLMResponse:
        del temperature, sample_idx
        matches = [marker for marker in self.script if marker in prompt]
        if not matches:
            raise KeyError(f"No FakeLLM response matches prompt: {prompt!r}")

        response = self.script[max(matches, key=len)]
        text = json.dumps(response, sort_keys=True)
        self.calls += 1
        return LLMResponse(
            text=text,
            json=response.copy(),
            tokens_in=len(prompt.split()),
            tokens_out=len(text.split()),
            model=self.model,
        )
