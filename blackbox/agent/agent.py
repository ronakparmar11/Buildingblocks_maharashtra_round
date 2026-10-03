import logging
import re
from typing import Any

from blackbox.agent.prompts import (
    check_prompt,
    extract_prompt,
    plan_prompt,
    reformulate_prompt,
    synthesize_prompt,
)
from blackbox.agent.scoring import f1, is_pass
from blackbox.sdk.cassette import Usage
from blackbox.sdk.context import ExecutionContext
from blackbox.store.models import Run, Task
from blackbox.store.repo import finish_run, get_run

logger = logging.getLogger(__name__)


def _fallback_plan(question: str) -> dict[str, Any]:
    return {
        "type": "bridge",
        "subquestions": [{"id": "q1", "text": question, "deps": []}],
    }


def _normalize_plan(output: dict[str, Any], question: str) -> dict[str, Any]:
    plan_type = output.get("type")
    raw_nodes = output.get("subquestions")
    if plan_type not in {"bridge", "comparison"} or not isinstance(raw_nodes, list):
        return _fallback_plan(question)

    nodes: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw_node in raw_nodes[:3]:
        if not isinstance(raw_node, dict):
            return _fallback_plan(question)
        node_id = raw_node.get("id")
        text = raw_node.get("text")
        deps = raw_node.get("deps")
        if (
            not isinstance(node_id, str)
            or not isinstance(text, str)
            or not isinstance(deps, list)
            or not all(isinstance(dep, str) for dep in deps)
            or node_id in seen
        ):
            return _fallback_plan(question)
        nodes.append({"id": node_id, "text": text, "deps": deps})
        seen.add(node_id)
    if not nodes or any(dep not in seen for node in nodes for dep in node["deps"]):
        return _fallback_plan(question)
    if _topological_order(nodes) is None:
        return _fallback_plan(question)
    return {"type": plan_type, "subquestions": nodes}


def _topological_order(nodes: list[dict[str, Any]]) -> list[dict[str, Any]] | None:
    remaining = {node["id"]: node for node in nodes}
    completed: set[str] = set()
    ordered: list[dict[str, Any]] = []
    while remaining:
        ready = sorted(
            node_id
            for node_id, node in remaining.items()
            if set(node["deps"]).issubset(completed)
        )
        if not ready:
            return None
        node_id = ready[0]
        ordered.append(remaining.pop(node_id))
        completed.add(node_id)
    return ordered


def _fill_placeholders(text: str, subanswers: dict[str, str]) -> str:
    return re.sub(
        r"\{([^{}]+)\}", lambda match: subanswers.get(match.group(1), ""), text
    )


def _retrieval_call(ctx: ExecutionContext, input_data: dict[str, Any]) -> dict[str, Any]:
    assert ctx.retriever is not None
    query = str(input_data["query"])
    k = int(input_data["k"])
    return {"passages": list(ctx.retriever.search(query, k=k))}


def run_agent(task: Task, ctx: ExecutionContext) -> Run:
    if ctx.tracer is None or ctx.retriever is None:
        raise ValueError("ExecutionContext requires tracer and retriever")
    if ctx.task.task_id != task.task_id:
        raise ValueError("Task does not match the execution context")

    tracer = ctx.tracer
    state: dict[str, Any] = {
        "plan": None,
        "subanswers": {},
        "attempts": {},
        "final": None,
    }
    ctx.state_snapshot = lambda: {
        "plan": state["plan"],
        "subanswers": dict(state["subanswers"]),
        "attempts": dict(state["attempts"]),
        "final": state["final"],
    }

    try:
        with tracer.run_scope(ctx):
            prompt = plan_prompt(task.question)
            plan_output = tracer.step(
                key="plan",
                name="plan",
                type="llm",
                node_id="root",
                attempt=0,
                deps=[],
                input={"question": task.question, "prompt": prompt},
                fn=tracer.llm_call,
                output_text_fn=lambda output: (
                    f"{output.get('type', 'invalid')}: "
                    f"{len(output.get('subquestions', []))} subquestions"
                ),
            )
            plan = _normalize_plan(plan_output, task.question)
            state["plan"] = plan
            ordered_nodes = _topological_order(plan["subquestions"])
            assert ordered_nodes is not None
            final_extract_keys: dict[str, str] = {}

            for node in ordered_nodes:
                node_id = node["id"]
                subquestion = str(node["text"])
                query = _fill_placeholders(subquestion, state["subanswers"])
                attempt = 0
                while True:
                    state["attempts"][node_id] = attempt
                    retrieve_key = f"{node_id}/retrieve#{attempt}"
                    retrieve_deps = ["plan"] + [
                        final_extract_keys[dep] for dep in node["deps"]
                    ]
                    if attempt > 0:
                        retrieve_deps.append(f"{node_id}/reformulate#{attempt - 1}")
                    retrieval = tracer.step(
                        key=retrieve_key,
                        name="retrieve",
                        type="retrieval",
                        node_id=node_id,
                        attempt=attempt,
                        deps=retrieve_deps,
                        input={"query": query, "k": 3},
                        fn=lambda input_data, params: (
                            _retrieval_call(ctx, input_data),
                            Usage(tokens_in=0, tokens_out=0, model="retriever"),
                        ),
                        output_text_fn=lambda output: (
                            f"{len(output.get('passages', []))} passages: "
                            + ", ".join(
                                str(passage.get("title", ""))
                                for passage in output.get("passages", [])
                            )
                        ),
                    )
                    passages = retrieval.get("passages", [])
                    if not isinstance(passages, list):
                        passages = []

                    extract_key = f"{node_id}/extract#{attempt}"
                    extract = tracer.step(
                        key=extract_key,
                        name="extract",
                        type="llm",
                        node_id=node_id,
                        attempt=attempt,
                        deps=[retrieve_key],
                        input={
                            "subquestion": subquestion,
                            "passages": passages,
                            "prompt": extract_prompt(subquestion, passages),
                        },
                        fn=tracer.llm_call,
                        output_text_fn=lambda output: str(output.get("answer", "")),
                    )
                    answer = str(extract.get("answer", ""))
                    final_extract_keys[node_id] = extract_key

                    check_key = f"{node_id}/check#{attempt}"
                    check = tracer.step(
                        key=check_key,
                        name="check",
                        type="llm",
                        node_id=node_id,
                        attempt=attempt,
                        deps=[retrieve_key, extract_key],
                        input={
                            "subquestion": subquestion,
                            "answer": answer,
                            "passages": passages,
                            "prompt": check_prompt(subquestion, answer, passages),
                        },
                        fn=tracer.llm_call,
                        output_text_fn=lambda output: (
                            f"supported={bool(output.get('supported'))}: "
                            f"{output.get('reason', '')}"
                        ),
                    )
                    if check.get("supported") is True or attempt >= 2:
                        state["subanswers"][node_id] = answer
                        break

                    reformulate_key = f"{node_id}/reformulate#{attempt}"
                    reformulated = tracer.step(
                        key=reformulate_key,
                        name="reformulate",
                        type="llm",
                        node_id=node_id,
                        attempt=attempt,
                        deps=[check_key],
                        input={
                            "subquestion": subquestion,
                            "previous_query": query,
                            "previous_answer": answer,
                            "prompt": reformulate_prompt(subquestion, query, answer),
                        },
                        fn=tracer.llm_call,
                        output_text_fn=lambda output: str(output.get("query", "")),
                    )
                    query = str(reformulated.get("query", ""))
                    attempt += 1

            synth_prompt = synthesize_prompt(task.question, state["subanswers"])
            synthesis = tracer.step(
                key="synthesize",
                name="synthesize",
                type="llm",
                node_id="root",
                attempt=0,
                deps=[final_extract_keys[node["id"]] for node in ordered_nodes],
                input={
                    "question": task.question,
                    "subanswers": dict(state["subanswers"]),
                    "prompt": synth_prompt,
                },
                fn=tracer.llm_call,
                output_text_fn=lambda output: str(output.get("answer", "")),
            )
            state["final"] = str(synthesis.get("answer", ""))
    except Exception:
        logger.exception("Agent run %s failed", ctx.run_id)
        run = get_run(tracer.session, ctx.run_id)
        if run is None:
            raise RuntimeError(f"Run was not persisted: {ctx.run_id}")
        return run

    score = f1(state["final"], task.gold_answer)
    return finish_run(
        tracer.session,
        ctx.run_id,
        final_answer=state["final"],
        outcome="pass" if is_pass(state["final"], task.gold_answer) else "fail",
        score_f1=score,
    )