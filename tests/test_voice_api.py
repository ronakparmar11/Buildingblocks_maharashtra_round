from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from blackbox.api import app
from blackbox.config import get_settings
from blackbox.llm.base import LLMResponse


class StubGemini:
    prompt = ""

    def __init__(self, model: str | None = None) -> None:
        assert model == "gemini-3.5-flash-lite"

    def complete_json(
        self, prompt: str, temperature: float, sample_idx: int = 0
    ) -> LLMResponse:
        del temperature, sample_idx
        StubGemini.prompt = prompt
        return LLMResponse(
            text='{"answer":"You have 15 days from delivery."}',
            json={"answer": "You have 15 days from delivery."},
            tokens_in=87,
            tokens_out=11,
            model="gemini-test",
        )


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setenv("BLACKBOX_MOCK_API", "1")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setattr("blackbox.api.voice.GeminiLLM", StubGemini)
    get_settings.cache_clear()
    with TestClient(app) as test_client:
        yield test_client
    get_settings.cache_clear()


def test_voice_answer_uses_gemini_with_mock_catalog(client: TestClient) -> None:
    response = client.post(
        "/api/voice/answer?workspace=nimbu",
        json={
            "transcript": (
                "I bought a bedsheet in the Diwali sale. How long can I return it?"
            )
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == "You have 15 days from delivery."
    assert body["model"] == "gemini-test"
    assert body["tokens_in"] == 87
    assert "Returns during the Diwali sale" in body["sources"]
    assert "MOCK HELP-CENTER ARTICLES" in StubGemini.prompt
    assert "CUSTOMER TRANSCRIPT" in StubGemini.prompt
