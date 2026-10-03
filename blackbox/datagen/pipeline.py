import json
import logging
from collections import defaultdict
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from pathlib import Path
from random import Random
from threading import Event
from typing import Any, Literal
from uuid import uuid4

from sqlalchemy import case, func
from sqlmodel import Session, select

from blackbox.agent.agent import run_agent
from blackbox.config import get_settings
from blackbox.corpus.retriever import Retriever, get_retriever
from blackbox.faults.inject import _execute_fault
from blackbox.faults.library import FAULT_TYPES
from blackbox.faults.targets import applicable_targets, latest_clean_run
from blackbox.labeling.bisect import _label_fault_run
from blackbox.labeling.counterfactual import _label_organic_run
from blackbox.llm.base import LLMClient
from blackbox.llm.gemini import GeminiLLM
from blackbox.llm.groq import GroqLLM
from blackbox.replay.engine import _replay
from blackbox.sdk.cassette import Cassette as CassetteStore
from blackbox.sdk.context import ExecutionContext
from blackbox.sdk.tracer import Tracer
from blackbox.store.db import get_session, init_db
from blackbox.store.models import Cassette, Fault, Label, Run, Step, Task

logger = logging.getLogger(__name__)

Stage = Literal["all", "clean", "faults", "label", "organic"]
Worker = Callable[[str], None]


def _llm_client() -> LLMClient:
    settings = get_settings()
    if settings.LLM_PROVIDER == "gemini":
        return GeminiLLM()
    if settings.LLM_PROVIDER == "groq":
        return GroqLLM()
    raise ValueError("LLM_PROVIDER=fake is only supported in tests")


def _execute_clean(
    session: Session,
    task: Task,
    llm: LLMClient,
    retriever: Retriever,
) -> Run:
    tracer = Tracer(session, CassetteStore(session), llm=llm)
    context = ExecutionContext(
        run_id=uuid4().hex,
        task=task,
        origin="clean",
        demo_mode=bool(get_settings().BLACKBOX_DEMO_MODE),
        tracer=tracer,
        retriever=retriever,
    )
    return run_agent(task, context)


class DataGenerationPipeline:
    def __init__(
        self,
        llm: LLMClient | None = None,
        retriever: Retriever | None = None,
        workspace: str = "hotpot",
    ) -> None:
        self.settings = get_settings()
        self.llm = llm or _llm_client()
        self.workspace = workspace
        self.retriever = retriever or get_retriever(workspace)
        self._stop = Event()

    def run(self, stage: Stage, limit_tasks: int | None = None) -> None:
        init_db()
        task_ids = self._task_ids(limit_tasks)
        stages: tuple[Stage, ...] = (
            ("clean", "faults", "label", "organic") if stage == "all" else (stage,)
        )
        for current_stage in stages:
            if self._stop.is_set():
                break
            stage_task_ids = (
                self._organic_task_ids(task_ids)
                if current_stage == "organic"
                else task_ids
            )
            logger.info(
                "Starting %s stage for %d tasks", current_stage, len(stage_task_ids)
            )
            worker = getattr(self, f"_{current_stage}_task")
            self._run_workers(stage_task_ids, worker)
        write_datagen_report()

    def _task_ids(self, limit_tasks: int | None) -> list[str]:
        with get_session() as session:
            statement = (
                select(Task.task_id)
                .where(Task.workspace == self.workspace)
                .order_by(Task.task_id)
            )
            if limit_tasks is not None:
                statement = statement.limit(limit_tasks)
            return list(session.exec(statement).all())

    def _organic_task_ids(self, task_ids: list[str]) -> list[str]:
        if not task_ids:
            return []
        with get_session() as session:
            labeled = session.exec(
                select(func.count())
                .select_from(Label)
                .where(Label.method == "counterfactual")
            ).one()
            remaining = max(0, 60 - labeled)
            if not remaining:
                return []
            return list(
                session.exec(
                    select(Run.task_id)
                    .outerjoin(Label, Label.run_id == Run.run_id)
                    .where(
                        Run.task_id.in_(task_ids),
                        Run.origin == "clean",
                        Run.outcome == "fail",
                        Label.run_id.is_(None),
                    )
                    .order_by(Run.created_at)
                    .limit(remaining)
                ).all()
            )

    def _run_workers(self, task_ids: list[str], worker: Worker) -> None:
        executor = ThreadPoolExecutor(max_workers=self.settings.MAX_CONCURRENCY)
        futures: dict[Future[None], str] = {
            executor.submit(worker, task_id): task_id for task_id in task_ids
        }
        try:
            for future in as_completed(futures):
                task_id = futures[future]
                try:
                    future.result()
                except Exception:
                    logger.exception("Generation failed for task %s", task_id)
        except KeyboardInterrupt:
            self._stop.set()
            logger.warning("Generation interrupted; cancelling pending tasks")
            for future in futures:
                future.cancel()
            raise
        finally:
            executor.shutdown(wait=not self._stop.is_set(), cancel_futures=True)

    def _clean_task(self, task_id: str) -> None:
        if self._stop.is_set():
            return
        with get_session() as session:
            existing = session.exec(
                select(Run.run_id).where(
                    Run.task_id == task_id,
                    Run.origin == "clean",
                    Run.outcome.in_(("pass", "fail")),
                )
            ).first()
            if existing is not None:
                return
            task = session.get(Task, task_id)
            if task is not None:
                _execute_clean(session, task, self.llm, self.retriever)

    def _faults_task(self, task_id: str) -> None:
        if self._stop.is_set():
            return
        with get_session() as session:
            clean_run = latest_clean_run(session, task_id)
            task = session.get(Task, task_id)
            if clean_run is None or task is None:
                return
            existing = set(
                session.exec(
                    select(Fault.fault_type, Fault.step_key)
                    .join(Run, Run.run_id == Fault.run_id)
                    .where(Run.task_id == task_id)
                ).all()
            )
            targets: dict[str, list[str]] = defaultdict(list)
            for fault_type, step_key in applicable_targets(clean_run):
                targets[fault_type].append(step_key)
            for fault_type in FAULT_TYPES:
                candidates = sorted(targets[fault_type])
                Random(f"{self.settings.SEED}:{task_id}:{fault_type}").shuffle(
                    candidates
                )
                for step_key in candidates[:2]:
                    if self._stop.is_set():
                        return
                    if (fault_type, step_key) in existing:
                        continue
                    _execute_fault(
                        session,
                        task,
                        fault_type,
                        step_key,
                        self.settings.SEED,
                        self.llm,
                        self.retriever,
                    )

    def _label_task(self, task_id: str) -> None:
        if self._stop.is_set():
            return
        with get_session() as session:
            run_ids = list(
                session.exec(
                    select(Run.run_id)
                    .join(Fault, Fault.run_id == Run.run_id)
                    .outerjoin(Label, Label.run_id == Run.run_id)
                    .where(
                        Run.task_id == task_id,
                        Run.outcome == "fail",
                        Label.run_id.is_(None),
                    )
                    .order_by(Run.created_at)
                ).all()
            )

            def replay_fn(source_run_id: str, **kwargs: Any) -> Run:
                return _replay(
                    session,
                    source_run_id,
                    self.llm,
                    self.retriever,
                    **kwargs,
                )

            for run_id in run_ids:
                if self._stop.is_set():
                    return
                _label_fault_run(session, run_id, replay_fn)

    def _organic_task(self, task_id: str) -> None:
        if self._stop.is_set():
            return
        with get_session() as session:
            run_id = session.exec(
                select(Run.run_id)
                .outerjoin(Label, Label.run_id == Run.run_id)
                .where(
                    Run.task_id == task_id,
                    Run.origin == "clean",
                    Run.outcome == "fail",
                    Label.run_id.is_(None),
                )
                .order_by(Run.created_at)
            ).first()
            if run_id is None:
                return

            def replay_fn(source_run_id: str, **kwargs: Any) -> Run:
                return _replay(
                    session,
                    source_run_id,
                    self.llm,
                    self.retriever,
                    **kwargs,
                )

            _label_organic_run(session, run_id, replay_fn)


def datagen_status() -> dict[str, Any]:
    init_db()
    with get_session() as session:
        tasks = session.exec(select(func.count()).select_from(Task)).one()
        clean_total, clean_passed = session.exec(
            select(
                func.count(Run.run_id),
                func.sum(case((Run.outcome == "pass", 1), else_=0)),
            ).where(Run.origin == "clean", Run.outcome.in_(("pass", "fail")))
        ).one()
        fault_rows = session.exec(
            select(
                Fault.fault_type,
                func.count(Run.run_id),
                func.sum(case((Run.outcome == "fail", 1), else_=0)),
            )
            .join(Run, Run.run_id == Fault.run_id)
            .group_by(Fault.fault_type)
        ).all()
        labels_total, labels_verified, labels_matching = session.exec(
            select(
                func.count(Label.run_id),
                func.sum(case((Label.verified.is_(True), 1), else_=0)),
                func.sum(case((Label.matches_injection.is_(True), 1), else_=0)),
            ).where(Label.method == "bisect")
        ).one()
        organic_labels = session.exec(
            select(func.count())
            .select_from(Label)
            .where(Label.method == "counterfactual")
        ).one()
        llm_steps, cache_hits = session.exec(
            select(
                func.count(Step.step_id),
                func.sum(case((Step.cache_hit.is_(True), 1), else_=0)),
            ).where(Step.type == "llm", Step.reused.is_(False))
        ).one()
        total_tokens = session.exec(select(func.sum(Run.tokens_total))).one() or 0
        cassette_entries = session.exec(
            select(func.count()).select_from(Cassette)
        ).one()

    clean_total = int(clean_total or 0)
    clean_passed = int(clean_passed or 0)
    labels_total = int(labels_total or 0)
    labels_verified = int(labels_verified or 0)
    labels_matching = int(labels_matching or 0)
    llm_steps = int(llm_steps or 0)
    cache_hits = int(cache_hits or 0)
    return {
        "tasks": int(tasks),
        "clean": {
            "runs": clean_total,
            "passed": clean_passed,
            "pass_rate": clean_passed / clean_total if clean_total else 0.0,
        },
        "faults": {
            fault_type: {
                "runs": int(total),
                "failed": int(failed or 0),
                "failure_rate": int(failed or 0) / int(total),
            }
            for fault_type, total, failed in fault_rows
        },
        "labels": {
            "total": labels_total,
            "verified": labels_verified,
            "verified_rate": labels_verified / labels_total if labels_total else 0.0,
            "matches_injection": labels_matching,
            "matches_injection_rate": (
                labels_matching / labels_total if labels_total else 0.0
            ),
        },
        "organic_labels": int(organic_labels),
        "cassette": {
            "entries": int(cassette_entries),
            "hits": cache_hits,
            "calls": llm_steps,
            "hit_rate": cache_hits / llm_steps if llm_steps else 0.0,
        },
        "total_tokens": int(total_tokens),
    }


def write_datagen_report() -> dict[str, Any]:
    report = datagen_status()
    path = Path(get_settings().ARTIFACTS_DIR) / "datagen_report.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    return report
