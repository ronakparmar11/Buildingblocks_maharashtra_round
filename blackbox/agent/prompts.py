import json
from typing import Any

PLAN_PROMPT = """[PLAN]
Decompose the question into at most 3 short research subquestions. Infer whether it
is bridge or comparison. Comparison branches must be independent. Bridge questions
must put the earlier answer into later text as a {q1} placeholder and list q1 in deps.

Comparison example:
Question: Which film was released first, Alpha or Beta?
{"type":"comparison","subquestions":[{"id":"q1","text":"When was Alpha released?","deps":[]},{"id":"q2","text":"When was Beta released?","deps":[]}]}

Bridge example:
Question: Where was the author of Alpha born?
{"type":"bridge","subquestions":[{"id":"q1","text":"Who wrote Alpha?","deps":[]},{"id":"q2","text":"Where was {q1} born?","deps":["q1"]}]}

Return only one strict JSON object with exactly this shape:
{"type":"bridge|comparison","subquestions":[{"id":"q1","text":"...","deps":[]}]}
Question: {question}"""

PLAN_QTYPE_PROMPT = """[PLAN:QTYPE]
Decompose the question into at most 3 short research subquestions. The known
question type is {qtype}; preserve that structure explicitly. Comparison branches
must be independent. Bridge questions must put the earlier answer into later text
as a {{q1}} placeholder and list q1 in deps.

Return only one strict JSON object with exactly this shape:
{{"type":"bridge|comparison","subquestions":[{{"id":"q1","text":"...","deps":[]}}]}}
Question: {question}"""

EXTRACT_PROMPT = """[EXTRACT]
Answer the subquestion from the passages. Use a short span. Return only one strict
JSON object with exactly this shape:
{"answer":"...","evidence_pid":"...","evidence_sentence":"..."}
Subquestion: {subquestion}
Passages: {passages}"""

EXTRACT_QUOTE_PROMPT = """[EXTRACT:QUOTE]
First identify the exact supporting sentence, then answer the subquestion using a
short span from that sentence. Return only one strict JSON object with exactly this
shape:
{"answer":"...","evidence_pid":"...","evidence_sentence":"..."}
Subquestion: {subquestion}
Passages: {passages}"""

CHECK_PROMPT = """[CHECK]
Decide whether the answer is directly supported by the passages. Return only one
strict JSON object with exactly this shape:
{"supported":true,"reason":"..."}
Subquestion: {subquestion}
Answer: {answer}
Passages: {passages}"""

REFORMULATE_PROMPT = """[REFORMULATE]
Write a better retrieval query after an unsupported answer. Return only one strict
JSON object with exactly this shape: {"query":"..."}
Subquestion: {subquestion}
Previous query: {previous_query}
Previous answer: {previous_answer}"""

SYNTHESIZE_PROMPT = """[SYNTHESIZE]
Answer the original question using the subanswers. Return a short span, using yes or
no for a yes/no comparison. Return only one strict JSON object with exactly this
shape: {"answer":"..."}
Question: {question}
Subanswers: {subanswers}"""

SYNTHESIZE_STRICT_PROMPT = """[SYNTHESIZE:STRICT]
Answer the original question using only the supplied subanswers. Do not add facts
or entities that are absent from them. Return a short span, using yes or no for a
yes/no comparison. Return only one strict JSON object with exactly this shape:
{"answer":"..."}
Question: {question}
Subanswers: {subanswers}"""

REWRITE_QUERY_PROMPT = """[REPAIR:QUERY]
Rewrite the search query so it retrieves evidence for the subquestion. Keep named
entities and remove conversational filler. Return only one strict JSON object with
exactly this shape: {"query":"..."}
Subquestion: {subquestion}
Previous query: {query}"""


def plan_prompt(question: str, variant: str | None = None, qtype: str = "") -> str:
    if variant == "qtype":
        return PLAN_QTYPE_PROMPT.format(question=question, qtype=qtype)
    return PLAN_PROMPT.replace("{question}", question)


def extract_prompt(
    subquestion: str,
    passages: list[dict[str, Any]],
    variant: str | None = None,
) -> str:
    template = EXTRACT_QUOTE_PROMPT if variant == "quote_evidence" else EXTRACT_PROMPT
    return template.replace("{subquestion}", subquestion).replace(
        "{passages}",
        json.dumps(passages, ensure_ascii=False, separators=(",", ":")),
    )


def check_prompt(
    subquestion: str, answer: str, passages: list[dict[str, Any]]
) -> str:
    return (
        CHECK_PROMPT.replace("{subquestion}", subquestion)
        .replace("{answer}", answer)
        .replace(
            "{passages}",
            json.dumps(passages, ensure_ascii=False, separators=(",", ":")),
        )
    )


def reformulate_prompt(
    subquestion: str, previous_query: str, previous_answer: str
) -> str:
    return (
        REFORMULATE_PROMPT.replace("{subquestion}", subquestion)
        .replace("{previous_query}", previous_query)
        .replace("{previous_answer}", previous_answer)
    )


def rewrite_query_prompt(subquestion: str, query: str) -> str:
    return REWRITE_QUERY_PROMPT.replace("{subquestion}", subquestion).replace(
        "{query}", query
    )


def synthesize_prompt(
    question: str,
    subanswers: dict[str, str],
    variant: str | None = None,
) -> str:
    template = (
        SYNTHESIZE_STRICT_PROMPT
        if variant == "strict_subanswers"
        else SYNTHESIZE_PROMPT
    )
    return template.replace("{question}", question).replace(
        "{subanswers}",
        json.dumps(subanswers, ensure_ascii=False, separators=(",", ":")),
    )