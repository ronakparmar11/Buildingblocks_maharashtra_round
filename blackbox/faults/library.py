import re
from random import Random
from typing import Any

from blackbox.sdk.tracer import register_fault
from blackbox.store.models import Task

PLAN_CORRUPT = "PLAN_CORRUPT"
BAD_QUERY = "BAD_QUERY"
DISTRACTOR_RETRIEVAL = "DISTRACTOR_RETRIEVAL"
TRUNCATED_CONTEXT = "TRUNCATED_CONTEXT"
WRONG_EXTRACTION = "WRONG_EXTRACTION"
HALLUCINATED_SYNTHESIS = "HALLUCINATED_SYNTHESIS"

FAULT_TYPES = (
    PLAN_CORRUPT,
    BAD_QUERY,
    DISTRACTOR_RETRIEVAL,
    TRUNCATED_CONTEXT,
    WRONG_EXTRACTION,
    HALLUCINATED_SYNTHESIS,
)


def _candidates(fault_params: dict[str, Any]) -> list[dict[str, str]]:
    raw_candidates = fault_params.get("distractors", [])
    if not isinstance(raw_candidates, list):
        return []
    return [
        {
            "pid": str(item["pid"]),
            "title": str(item["title"]),
            "text": str(item["text"]),
        }
        for item in raw_candidates
        if isinstance(item, dict)
        and all(isinstance(item.get(key), str) for key in ("pid", "title", "text"))
    ]


def _seed(fault_params: dict[str, Any]) -> int:
    return int(fault_params.get("seed", 0))


def corrupt_plan(
    value: dict[str, Any],
    task: Task,
    fault_params: dict[str, Any],
    rng: Random,
) -> tuple[dict[str, Any], dict[str, Any]]:
    output = dict(value)
    raw_nodes = value.get("subquestions", [])
    nodes = [dict(node) for node in raw_nodes if isinstance(node, dict)]
    if value.get("type") == "comparison" and len(nodes) > 1:
        removed = nodes.pop()
        output["subquestions"] = nodes
        return output, {
            "seed": _seed(fault_params),
            "removed_node": str(removed.get("id", "")),
        }

    candidates = _candidates(fault_params)
    matching = [
        node for node in nodes if re.search(r"\{[^{}]+\}", str(node.get("text", "")))
    ]
    if value.get("type") == "bridge" and matching and candidates:
        node = rng.choice(matching)
        distractor = rng.choice(candidates)
        node["text"] = re.sub(
            r"\{[^{}]+\}", distractor["title"], str(node["text"]), count=1
        )
        output["subquestions"] = nodes
        return output, {
            "seed": _seed(fault_params),
            "distractor_pid": distractor["pid"],
            "distractor_title": distractor["title"],
            "node_id": str(node.get("id", "")),
        }
    return output, {"seed": _seed(fault_params)}


def bad_query(
    value: dict[str, Any],
    task: Task,
    fault_params: dict[str, Any],
    rng: Random,
) -> tuple[dict[str, Any], dict[str, Any]]:
    del task
    output = dict(value)
    query = str(value.get("query", ""))
    candidates = _candidates(fault_params)
    if not candidates:
        return output, {"seed": _seed(fault_params)}
    distractor = rng.choice(candidates)
    entity = str(fault_params.get("entity", ""))
    if entity and entity.casefold() in query.casefold():
        query = re.sub(
            re.escape(entity), distractor["title"], query, count=1, flags=re.IGNORECASE
        )
    else:
        spans = re.findall(r"\b[A-Z][\w'-]*(?:\s+[A-Z][\w'-]*)*\b", query)
        if spans:
            entity = max(spans, key=len)
            query = query.replace(entity, distractor["title"], 1)
    output["query"] = query
    return output, {
        "seed": _seed(fault_params),
        "distractor_pid": distractor["pid"],
        "distractor_title": distractor["title"],
        "replaced_entity": entity,
    }


def distractor_retrieval(
    value: dict[str, Any],
    task: Task,
    fault_params: dict[str, Any],
    rng: Random,
) -> tuple[dict[str, Any], dict[str, Any]]:
    passages = [
        dict(passage)
        for passage in value.get("passages", [])
        if isinstance(passage, dict)
    ]
    candidates = _candidates(fault_params)
    rng.shuffle(candidates)
    replacements: list[str] = []
    candidate_index = 0
    for index, passage in enumerate(passages):
        if passage.get("title") not in task.gold_titles or not candidates:
            continue
        distractor = candidates[candidate_index % len(candidates)]
        candidate_index += 1
        passages[index] = {**distractor, "score": passage.get("score", 0.0)}
        replacements.append(distractor["pid"])
    return {**value, "passages": passages}, {
        "seed": _seed(fault_params),
        "distractor_pids": replacements,
    }


def truncated_context(
    value: dict[str, Any],
    task: Task,
    fault_params: dict[str, Any],
    rng: Random,
) -> tuple[dict[str, Any], dict[str, Any]]:
    del task, rng
    passages = []
    truncated_pids: list[str] = []
    for raw_passage in value.get("passages", []):
        if not isinstance(raw_passage, dict):
            continue
        passage = dict(raw_passage)
        text = str(passage.get("text", ""))
        first_sentence = re.split(r"(?<=[.!?])\s+", text, maxsplit=1)[0]
        passage["text"] = first_sentence
        passages.append(passage)
        if first_sentence != text:
            truncated_pids.append(str(passage.get("pid", "")))
    return {**value, "passages": passages}, {
        "seed": _seed(fault_params),
        "truncated_pids": truncated_pids,
    }


def wrong_extraction(
    value: dict[str, Any],
    task: Task,
    fault_params: dict[str, Any],
    rng: Random,
) -> tuple[dict[str, Any], dict[str, Any]]:
    del task
    output = dict(value)
    answer = str(value.get("answer", ""))
    raw_alternatives = fault_params.get("alternatives", [])
    alternatives = [
        str(item)
        for item in raw_alternatives
        if str(item).casefold() != answer.casefold()
    ]
    if alternatives:
        replacement = rng.choice(alternatives)
        output["answer"] = replacement
        return output, {"seed": _seed(fault_params), "replacement": replacement}
    return output, {"seed": _seed(fault_params)}


def hallucinated_synthesis(
    value: dict[str, Any],
    task: Task,
    fault_params: dict[str, Any],
    rng: Random,
) -> tuple[dict[str, Any], dict[str, Any]]:
    output = dict(value)
    answer = str(value.get("answer", ""))
    if task.qtype == "comparison" and answer.casefold() in {"yes", "no"}:
        replacement = "no" if answer.casefold() == "yes" else "yes"
        output["answer"] = replacement
        return output, {"seed": _seed(fault_params), "replacement": replacement}

    raw_subanswers = fault_params.get("subanswers", {})
    alternatives = (
        [
            (str(node_id), str(subanswer))
            for node_id, subanswer in raw_subanswers.items()
            if str(subanswer).casefold() != answer.casefold()
        ]
        if isinstance(raw_subanswers, dict)
        else []
    )
    if alternatives:
        node_id, replacement = rng.choice(alternatives)
        output["answer"] = replacement
        return output, {
            "seed": _seed(fault_params),
            "source_node": node_id,
            "replacement": replacement,
        }
    return output, {"seed": _seed(fault_params)}


register_fault(PLAN_CORRUPT, output_fn=corrupt_plan)
register_fault(BAD_QUERY, input_fn=bad_query)
register_fault(DISTRACTOR_RETRIEVAL, output_fn=distractor_retrieval)
register_fault(TRUNCATED_CONTEXT, output_fn=truncated_context)
register_fault(WRONG_EXTRACTION, output_fn=wrong_extraction)
register_fault(HALLUCINATED_SYNTHESIS, output_fn=hallucinated_synthesis)
