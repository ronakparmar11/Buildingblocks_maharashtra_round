import json
import re
import time
from functools import lru_cache
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException

from blackbox.api.schemas import VoiceAnswerRequest, VoiceAnswerResponse
from blackbox.config import get_settings
from blackbox.corpus.paths import workspace_data_dir
from blackbox.llm.gemini import GeminiLLM

router = APIRouter()

_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")
_STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "can",
    "do",
    "for",
    "how",
    "i",
    "in",
    "is",
    "it",
    "my",
    "of",
    "on",
    "the",
    "to",
    "what",
    "when",
    "within",
}


def _tokens(value: str) -> set[str]:
    return set(_TOKEN_PATTERN.findall(value.casefold())) - _STOP_WORDS


@lru_cache(maxsize=8)
def _catalog(path: str) -> tuple[dict[str, Any], ...]:
    with Path(path).open(encoding="utf-8") as file:
        return tuple(json.loads(line) for line in file if line.strip())


def _relevant_articles(transcript: str, workspace: str, limit: int = 4) -> list[dict[str, Any]]:
    settings = get_settings()
    path = workspace_data_dir(settings, workspace) / "passages.jsonl"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Mock support catalog not found")
    query_tokens = _tokens(transcript)

    def score(article: dict[str, Any]) -> tuple[int, int]:
        title_overlap = len(query_tokens & _tokens(str(article.get("title", ""))))
        text_overlap = len(query_tokens & _tokens(str(article.get("text", ""))))
        return (title_overlap * 3 + text_overlap, title_overlap)

    current = [article for article in _catalog(str(path)) if article.get("status") == "current"]
    return sorted(current, key=score, reverse=True)[:limit]


@router.post("/voice/answer", response_model=VoiceAnswerResponse)
def answer_voice_request(
    request: VoiceAnswerRequest,
    workspace: str = "nimbu",
) -> VoiceAnswerResponse:
    settings = get_settings()
    if not settings.GEMINI_API_KEY:
        raise HTTPException(status_code=503, detail="Voice assistant is not configured")

    articles = _relevant_articles(request.transcript, workspace)
    context = "\n\n".join(
        f"[{index}] {article['title']}\n{article['text']}"
        for index, article in enumerate(articles, start=1)
    )
    prompt = f"""You are the voice support assistant for a fictional demo store called Nimbu Living.
Answer the customer using only the MOCK HELP-CENTER ARTICLES below.
Do not claim that you accessed an order, account, call recording, or production system.
If the articles do not contain the answer, say you do not have enough information.
Keep the answer natural, direct, and under 60 words because it will be spoken aloud.
Return exactly one JSON object with this shape: {{"answer": "your answer"}}.

MOCK HELP-CENTER ARTICLES
{context}

CUSTOMER TRANSCRIPT
{request.transcript}
"""
    started = time.perf_counter()
    try:
        result = GeminiLLM(model=settings.VOICE_LLM_MODEL).complete_json(
            prompt, temperature=0.2
        )
        answer = str(result.json.get("answer", "")).strip()
        if not answer:
            raise ValueError("Voice assistant returned an empty answer")
    except Exception as error:
        raise HTTPException(status_code=502, detail="Voice assistant is temporarily unavailable") from error

    return VoiceAnswerResponse(
        answer=answer,
        model=result.model,
        latency_ms=round((time.perf_counter() - started) * 1000),
        tokens_in=result.tokens_in,
        tokens_out=result.tokens_out,
        sources=[str(article["title"]) for article in articles],
    )
