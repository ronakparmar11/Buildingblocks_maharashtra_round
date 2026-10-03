import json
from typing import Any

from google import genai
from google.genai import types
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from blackbox.config import get_settings
from blackbox.llm.base import (
    LLMResponse,
    RateLimiter,
    is_retryable_error,
    parse_json_object,
)


class GeminiLLM:
    def __init__(
        self,
        model: str | None = None,
        api_key: str | None = None,
        rpm_limit: int | None = None,
        client: genai.Client | None = None,
    ) -> None:
        settings = get_settings()
        self.model = model or settings.LLM_MODEL
        self.client = client or genai.Client(api_key=api_key or settings.GEMINI_API_KEY)
        self._rate_limiter = RateLimiter(rpm_limit or settings.RPM_LIMIT)

    def complete_json(
        self, prompt: str, temperature: float, sample_idx: int = 0
    ) -> LLMResponse:
        del sample_idx
        response = self._generate(prompt, temperature)
        text, parsed, repaired = self._parse_or_repair(prompt, temperature, response)
        usages = [
            item.usage_metadata
            for item in (response, repaired)
            if item is not None and item.usage_metadata is not None
        ]
        return LLMResponse(
            text=text,
            json=parsed,
            tokens_in=sum(usage.prompt_token_count or 0 for usage in usages),
            tokens_out=sum(usage.candidates_token_count or 0 for usage in usages),
            model=(repaired or response).model_version or self.model,
        )

    def _parse_or_repair(
        self,
        prompt: str,
        temperature: float,
        response: types.GenerateContentResponse,
    ) -> tuple[str, dict[str, Any], types.GenerateContentResponse | None]:
        text = response.text or ""
        try:
            return text, parse_json_object(text), None
        except (json.JSONDecodeError, TypeError):
            repair_prompt = (
                f"{prompt}\n\nYour previous response was not valid JSON:\n{text}\n\n"
                "Return only one valid JSON object."
            )
            repaired = self._generate(repair_prompt, temperature)
            repaired_text = repaired.text or ""
            return repaired_text, parse_json_object(repaired_text), repaired

    @retry(
        retry=retry_if_exception(is_retryable_error),
        wait=wait_exponential(multiplier=1, min=1, max=30),
        stop=stop_after_attempt(4),
        reraise=True,
    )
    def _generate(
        self, prompt: str, temperature: float
    ) -> types.GenerateContentResponse:
        self._rate_limiter.wait()
        return self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=temperature,
                response_mime_type="application/json",
            ),
        )
