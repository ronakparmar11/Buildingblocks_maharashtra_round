import re
from dataclasses import dataclass

from blackbox.sdk.context import Override
from blackbox.store.models import Step

ASK_AGAIN = "Ask again (new sample)"
REPLAN_WITH_QTYPE = "Re-plan with the question type"
REWRITE_QUERY = "Rewrite the search query"
WIDEN_SEARCH = "Widen search to 6 results"
SEARCH_ENTITY = "Search by entity name"
QUOTE_EVIDENCE = "Quote evidence first, then answer"
USE_SUBANSWERS = "Use only the sub-answers"


@dataclass(frozen=True)
class RepairCandidate:
    display_name: str
    override: Override


def ask_again(sample_idx: int = 1) -> Override:
    return Override(
        kind="regenerate",
        params={"temperature": 0.8, "sample_idx": sample_idx},
    )


def replan_with_question_type() -> Override:
    return Override(kind="regenerate", params={"prompt_variant": "qtype"})


def rewrite_search_query(query: str) -> Override:
    return Override(kind="regenerate", params={"query": query})


def widen_search() -> Override:
    return Override(kind="regenerate", params={"k": 6})


def search_by_entity_name(entity: str) -> Override:
    return Override(
        kind="regenerate",
        params={"retrieval_mode": "title_entity", "entity": entity, "k": 3},
    )


def quote_evidence_first() -> Override:
    return Override(
        kind="regenerate", params={"prompt_variant": "quote_evidence"}
    )


def use_only_subanswers() -> Override:
    return Override(
        kind="regenerate", params={"prompt_variant": "strict_subanswers"}
    )


def _entity_from_query(query: str) -> str:
    phrases = re.findall(r"\b[A-Z][\w'-]*(?:\s+[A-Z][\w'-]*)*", query)
    ignored = {"What", "When", "Where", "Which", "Who", "Why", "How"}
    candidates = [phrase for phrase in phrases if phrase not in ignored]
    return max(candidates, key=len, default=query)


def candidates_for_step(
    step: Step, *, rewritten_query: str | None = None
) -> list[RepairCandidate]:
    if step.name == "plan":
        return [
            RepairCandidate(ASK_AGAIN, ask_again()),
            RepairCandidate(REPLAN_WITH_QTYPE, replan_with_question_type()),
        ]
    if step.name == "retrieve":
        query = str(step.input.get("query", ""))
        candidates: list[RepairCandidate] = []
        if rewritten_query:
            candidates.append(
                RepairCandidate(REWRITE_QUERY, rewrite_search_query(rewritten_query))
            )
        candidates.extend(
            [
                RepairCandidate(WIDEN_SEARCH, widen_search()),
                RepairCandidate(
                    SEARCH_ENTITY, search_by_entity_name(_entity_from_query(query))
                ),
            ]
        )
        return candidates
    if step.name == "extract":
        return [
            RepairCandidate(ASK_AGAIN, ask_again()),
            RepairCandidate(QUOTE_EVIDENCE, quote_evidence_first()),
        ]
    if step.name in {"check", "reformulate"}:
        return [RepairCandidate(ASK_AGAIN, ask_again())]
    if step.name == "synthesize":
        return [
            RepairCandidate(ASK_AGAIN, ask_again()),
            RepairCandidate(USE_SUBANSWERS, use_only_subanswers()),
        ]
    return []