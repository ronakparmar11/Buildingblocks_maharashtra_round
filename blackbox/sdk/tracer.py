import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from inspect import signature
from random import Random
from typing import Any

from sqlmodel import Session, select

from blackbox.config import get_settings
from blackbox.llm.base import LLMClient
from blackbox.sdk.cassette import Cassette, Usage
from blackbox.sdk.context import ExecutionContext, current_context
from blackbox.store.hashing import sha256_json
from blackbox.store.models import Run, Step, Task
from blackbox.store.repo import add_step, create_run, finish_run

FaultResult = tuple[dict[str, Any], dict[str, Any]]
FaultFn = Callable[[dict[str, Any], Task, dict[str, Any], Random], FaultResult]
LegacyFaultFn = Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]]
StepFn = Callable[[dict[str, Any], dict[str, Any]], tuple[dict[str, Any], Usage]]


@dataclass(frozen=True)
class _FaultHooks:
    input_fn: FaultFn | None = None
    output_fn: FaultFn | None = None


@dataclass
class _RunStats:
    started_at: float
    n_steps: int = 0
    n_reused: int = 0
    n_executed: int = 0
    tokens_total: int = 0
    tokens_saved: int = 0


_FAULTS: dict[str, _FaultHooks] = {}


def register_fault(
    fault_type: str,
    input_fn: FaultFn | LegacyFaultFn | None = None,
    output_fn: FaultFn | LegacyFaultFn | None = None,
) -> None:
    if input_fn is None and output_fn is None:
        raise ValueError("A fault must define an input or output hook")
    _FAULTS[fault_type] = _FaultHooks(
        input_fn=_adapt_fault(input_fn),
        output_fn=_adapt_fault(output_fn),
    )


def _adapt_fault(fault_fn: FaultFn | LegacyFaultFn | None) -> FaultFn | None:
    if fault_fn is None:
        return None
    if len(signature(fault_fn).parameters) != 2:
        return fault_fn  # type: ignore[return-value]

    def adapted(
        value: dict[str, Any],
        task: Task,
        fault_params: dict[str, Any],
        rng: Random,
    ) -> FaultResult:
        del task, rng
        legacy_result = fault_fn(value, fault_params)
        return legacy_result, dict(fault_params)

    return adapted


class Tracer:
    def __init__(
        self,
        session: Session,
        cassette: Cassette,
        llm: LLMClient | None = None,
        model: str | None = None,
    ) -> None:
        self.session = session
        self.cassette = cassette
        self.llm = llm
        self.model = model or getattr(llm, "model", None) or get_settings().LLM_MODEL
        self._stats: _RunStats | None = None

    @contextmanager
    def run_scope(self, ctx: ExecutionContext) -> Iterator[ExecutionContext]:
        if self._stats is not None:
            raise RuntimeError("Nested tracer run scopes are not supported")

        replay_spec = None
        if ctx.source_run_id is not None:
            replay_spec = {
                "overrides": {
                    key: {
                        "kind": override.kind,
                        "params": override.params,
                        "fault_type": override.fault_type,
                        "fault_params": override.fault_params,
                    }
                    for key, override in ctx.overrides.items()
                },
                "freeze_before_idx": ctx.freeze_before_idx,
            }
        create_run(
            self.session,
            Run(
                run_id=ctx.run_id,
                task_id=ctx.task.task_id,
                workspace=ctx.task.workspace,
                origin=ctx.origin,
                parent_run_id=ctx.source_run_id,
                final_answer=None,
                outcome="error",
                score_f1=0.0,
                n_steps=0,
                n_reused=0,
                n_executed=0,
                tokens_total=0,
                tokens_saved=0,
                latency_ms=0,
                replay_spec=replay_spec,
            ),
        )
        token = current_context.set(ctx)
        self._stats = _RunStats(started_at=time.perf_counter())
        previous_demo_mode = self.cassette.demo_mode
        self.cassette.demo_mode = previous_demo_mode or ctx.demo_mode
        failed = False
        try:
            yield ctx
        except BaseException:
            failed = True
            raise
        finally:
            stats = self._stats
            self._stats = None
            current_context.reset(token)
            self.cassette.demo_mode = previous_demo_mode
            if stats is not None:
                finish_run(
                    self.session,
                    ctx.run_id,
                    outcome="error" if failed else "pass",
                    n_steps=stats.n_steps,
                    n_reused=stats.n_reused,
                    n_executed=stats.n_executed,
                    tokens_total=stats.tokens_total,
                    tokens_saved=stats.tokens_saved,
                    latency_ms=round((time.perf_counter() - stats.started_at) * 1000),
                )

    def llm_call(
        self, input_data: dict[str, Any], params: dict[str, Any]
    ) -> tuple[dict[str, Any], Usage]:
        if self.llm is None:
            raise RuntimeError("Tracer has no LLM client")
        prompt = input_data.get("prompt")
        if not isinstance(prompt, str):
            raise TypeError("LLM step input must contain a string prompt")
        response = self.llm.complete_json(
            prompt,
            temperature=float(params.get("temperature", 0.0)),
            sample_idx=int(params.get("sample_idx", 0)),
        )
        return response.json, {
            "tokens_in": response.tokens_in,
            "tokens_out": response.tokens_out,
            "model": response.model,
        }

    def step(
        self,
        key: str,
        name: str,
        type: str,
        node_id: str,
        attempt: int,
        deps: list[str],
        input: dict[str, Any],
        fn: StepFn,
        output_text_fn: Callable[[dict[str, Any]], str],
    ) -> dict[str, Any]:
        ctx = current_context.get()
        stats = self._stats
        if ctx is None or stats is None:
            raise RuntimeError("Tracer.step() must run inside run_scope()")

        idx = stats.n_steps
        source = self._source_step(ctx.source_run_id, key)
        override = ctx.overrides.get(key)
        effective_input = input
        input_hash = sha256_json(input)
        meta: dict[str, Any] = {}
        output: dict[str, Any]
        usage: Usage = {"tokens_in": 0, "tokens_out": 0, "model": self.model}
        cache_hit = False
        reused = False
        overridden = override is not None
        latency_ms = 0
        started_at = time.perf_counter()

        try:
            if override is not None and override.kind == "set_output":
                if override.output is None:
                    raise ValueError(f"set_output override for {key} requires output")
                output = override.output
            elif override is None and self._can_reuse(source, input_hash, ctx):
                assert source is not None
                output = source.output
                usage["model"] = source.model or self.model
                reused = True
                meta = dict(source.meta)
                stats.n_reused += 1
                stats.tokens_saved += source.tokens_in + source.tokens_out
            else:
                params = dict(override.params) if override is not None else {}
                output_fault: FaultFn | None = None
                fault_params: dict[str, Any] = {}
                if override is not None and override.kind == "fault":
                    if (
                        override.fault_type is None
                        or override.fault_type not in _FAULTS
                    ):
                        raise ValueError(f"Unknown fault type: {override.fault_type}")
                    hooks = _FAULTS[override.fault_type]
                    fault_params = override.fault_params
                    rng = Random(int(fault_params.get("seed", 0)))
                    if hooks.input_fn is not None:
                        meta["pre_override_input_hash"] = input_hash
                        effective_input, used_params = hooks.input_fn(
                            input, ctx.task, dict(fault_params), rng
                        )
                        fault_params.clear()
                        fault_params.update(used_params)
                        input_hash = sha256_json(effective_input)
                    output_fault = hooks.output_fn

                output, usage, cache_hit = self.cassette.get_or_call(
                    kind="llm" if type == "llm" else "tool",
                    model=self.model,
                    payload={"input": effective_input, "params": params},
                    temperature=float(params.get("temperature", 0.0)),
                    sample_idx=int(params.get("sample_idx", 0)),
                    call_fn=lambda: fn(effective_input, params),
                )
                latency_ms = round((time.perf_counter() - started_at) * 1000)
                if output_fault is not None:
                    output, used_params = output_fault(
                        output, ctx.task, dict(fault_params), rng
                    )
                    fault_params.clear()
                    fault_params.update(used_params)
            output_text = output_text_fn(output)
        except Exception as error:
            latency_ms = round((time.perf_counter() - started_at) * 1000)
            add_step(
                self.session,
                Step(
                    run_id=ctx.run_id,
                    step_key=key,
                    idx=idx,
                    name=name,
                    type=type,
                    node_id=node_id,
                    attempt=attempt,
                    deps=deps,
                    input=effective_input,
                    input_hash=input_hash,
                    output={},
                    output_hash=sha256_json({}),
                    output_text="",
                    latency_ms=latency_ms,
                    tokens_in=0,
                    tokens_out=0,
                    model=self.model,
                    cache_hit=False,
                    reused=False,
                    overridden=overridden,
                    state_snapshot=ctx.state_snapshot(),
                    error=f"{error.__class__.__name__}: {error}",
                    meta=meta,
                ),
            )
            stats.n_steps += 1
            stats.n_executed += 1
            raise

        tokens_in = 0 if reused else usage.get("tokens_in", 0)
        tokens_out = 0 if reused else usage.get("tokens_out", 0)
        model = usage.get("model", self.model)
        add_step(
            self.session,
            Step(
                run_id=ctx.run_id,
                step_key=key,
                idx=idx,
                name=name,
                type=type,
                node_id=node_id,
                attempt=attempt,
                deps=deps,
                input=effective_input if not reused else input,
                input_hash=input_hash,
                output=output,
                output_hash=sha256_json(output),
                output_text=output_text,
                latency_ms=latency_ms,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                model=model,
                cache_hit=cache_hit,
                reused=reused,
                overridden=overridden,
                state_snapshot=ctx.state_snapshot(),
                error=None,
                meta=meta,
            ),
        )
        stats.n_steps += 1
        if not reused:
            stats.n_executed += 1
            if not cache_hit:
                stats.tokens_total += tokens_in + tokens_out
        return output

    def _source_step(self, run_id: str | None, key: str) -> Step | None:
        if run_id is None:
            return None
        statement = select(Step).where(Step.run_id == run_id, Step.step_key == key)
        return self.session.exec(statement).first()

    @staticmethod
    def _can_reuse(source: Step | None, input_hash: str, ctx: ExecutionContext) -> bool:
        if source is None:
            return False
        hashes_match = input_hash == source.input_hash or input_hash == source.meta.get(
            "pre_override_input_hash"
        )
        freeze_allows = (
            ctx.freeze_before_idx is None or source.idx < ctx.freeze_before_idx
        )
        return hashes_match and freeze_allows


@contextmanager
def run_scope(tracer: Tracer, ctx: ExecutionContext) -> Iterator[ExecutionContext]:
    with tracer.run_scope(ctx) as active_context:
        yield active_context
