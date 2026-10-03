import json
from typing import Any

from openai import OpenAI
from openai.types.chat import ChatCompletion
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from blackbox.config import get_settings
from blackbox.llm.base import (
    LLMResponse,
    RateLimiter,
    is_retryable_error,
    parse_json_object,
)


class GroqLLM:
    def __init__(
        self,
        model: str | None = None,
        api_key: str | None = None,
        rpm_limit: int | None = None,
        client: OpenAI | None = None,
    ) -> None:
        settings = get_settings()
        self.model = model or settings.GROQ_MODEL or settings.LLM_MODEL
        self.client = client or OpenAI(
            api_key=api_key or settings.GROQ_API_KEY,
            base_url="https://api.groq.com/openai/v1",
            max_retries=0,
        )
        self._rate_limiter = RateLimiter(rpm_limit or settings.RPM_LIMIT)

    def complete_json(
        self, prompt: str, temperature: float, sample_idx: int = 0
    ) -> LLMResponse:
        response = self._generate(prompt, temperature, sample_idx)
        text, parsed, repaired = self._parse_or_repair(
            prompt, temperature, sample_idx, response
        )
        usages = [
            item.usage
            for item in (response, repaired)
            if item is not None and item.usage is not None
        ]
        return LLMResponse(
            text=text,
            json=parsed,
            tokens_in=sum(usage.prompt_tokens for usage in usages),
            tokens_out=sum(usage.completion_tokens for usage in usages),
            model=(repaired or response).model,
        )

    def _parse_or_repair(
        self,
        prompt: str,
        temperature: float,
        sample_idx: int,
        response: ChatCompletion,
    ) -> tuple[str, dict[str, Any], ChatCompletion | None]:
        text = response.choices[0].message.content or ""
        try:
            return text, parse_json_object(text), None
        except (json.JSONDecodeError, TypeError):
            repair_prompt = (
                f"{prompt}\n\nYour previous response was not valid JSON:\n{text}\n\n"
                "Return only one valid JSON object."
            )
            repaired = self._generate(repair_prompt, temperature, sample_idx)
            repaired_text = repaired.choices[0].message.content or ""
            return repaired_text, parse_json_object(repaired_text), repaired

    @retry(
        retry=retry_if_exception(is_retryable_error),
        wait=wait_exponential(multiplier=1, min=1, max=30),
        stop=stop_after_attempt(4),
        reraise=True,
    )
    def _generate(
        self, prompt: str, temperature: float, sample_idx: int
    ) -> ChatCompletion:
        self._rate_limiter.wait()
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            seed=sample_idx,
            response_format={"type": "json_object"},
        )
        if not isinstance(response, ChatCompletion):
            raise TypeError("Streaming responses are not supported")
        return response
