import json
import logging
from pathlib import Path
from typing import Annotated
from uuid import uuid4

import typer
from rich.console import Console
from rich.logging import RichHandler
from rich.progress import Progress
from rich.table import Table
from sqlalchemy import func
from sqlmodel import Session, select

from blackbox.agent.agent import run_agent
from blackbox.config import get_settings
from blackbox.corpus.embed import build_embeddings
from blackbox.corpus.hotpot import build_hotpot_corpus
from blackbox.corpus.retriever import get_retriever
from blackbox.datagen.pipeline import (
    DataGenerationPipeline,
    Stage,
    datagen_status,
    write_datagen_report,
)
from blackbox.faults.inject import run_with_fault
from blackbox.faults.targets import applicable_targets, latest_clean_run
from blackbox.features.extract import build_dataset
from blackbox.labeling.bisect import label_fault_run
from blackbox.labeling.counterfactual import label_organic_run
from blackbox.llm.base import LLMClient
from blackbox.llm.gemini import GeminiLLM
from blackbox.llm.groq import GroqLLM
from blackbox.model.evaluate import evaluate
from blackbox.model.predict import diagnose
from blackbox.model.train import train_model
from blackbox.replay.compare import compare as compare_runs
from blackbox.replay.engine import replay as replay_run
from blackbox.sdk.cassette import Cassette as CassetteStore
from blackbox.sdk.context import ExecutionContext, Override
from blackbox.sdk.tracer import Tracer
from blackbox.store.db import get_session, init_db
from blackbox.store.models import Cassette, Fault, Label, Prediction, Run, Step, Task
from blackbox.store.repo import get_run, get_steps, get_task, list_tasks

app = typer.Typer(help="Black Box agent flight recorder.")
db_app = typer.Typer(help="Initialize and inspect the Black Box database.")
corpus_app = typer.Typer(help="Build and search the retrieval corpus.")
run_app = typer.Typer(help="Execute and inspect agent runs.")
faults_app = typer.Typer(help="List and inject realistic agent faults.")
label_app = typer.Typer(help="Label failed runs with counterfactual replay.")
generate_app = typer.Typer(help="Generate clean, fault, and labeled run data.")
features_app = typer.Typer(help="Build leakage-free step feature datasets.")
app.add_typer(db_app, name="db")
app.add_typer(corpus_app, name="corpus")
app.add_typer(run_app, name="run")
app.add_typer(faults_app, name="faults")
app.add_typer(label_app, name="label")
app.add_typer(generate_app, name="generate")
app.add_typer(features_app, name="features")

TABLES = (Task, Run, Fault, Step, Label, Prediction, Cassette)


def _not_implemented() -> None:
    typer.echo("not implemented yet")


@db_app.command("init")
def db_init() -> None:
    init_db()
    typer.echo("Database initialized.")


@db_app.command("stats")
def db_stats() -> None:
    init_db()
    with get_session() as session:
        for model in TABLES:
            count = session.exec(select(func.count()).select_from(model)).one()
            typer.echo(f"{model.__tablename__}: {count}")


@corpus_app.command("build")
def corpus_build(force: bool = typer.Option(False, "--force")) -> None:
    settings = get_settings()
    data_dir = Path(settings.DATA_DIR)
    outputs = [
        data_dir / "passages.jsonl",
        data_dir / "embeddings.npy",
        data_dir / "pid_index.json",
    ]
    if not force and all(path.exists() for path in outputs):
        typer.echo("Corpus files already exist; use --force to rebuild.")
        return

    tasks, passages = build_hotpot_corpus(settings)
    build_embeddings(settings)
    typer.echo(f"Built {len(tasks)} tasks and {len(passages)} passages.")


@corpus_app.command("search")
def corpus_search(query: str, k: int = typer.Option(3, min=1)) -> None:
    for result in get_retriever().search(query, k=k):
        typer.echo(f"{result['score']:.3f}\t{result['title']}\t{result['pid']}")


def _llm_client() -> LLMClient:
    settings = get_settings()
    if settings.LLM_PROVIDER == "gemini":
        return GeminiLLM()
    if settings.LLM_PROVIDER == "groq":
        return GroqLLM()
    raise typer.BadParameter("LLM_PROVIDER=fake is only supported in tests")


def _execute_clean(session: Session, task: Task, llm: LLMClient) -> Run:
    tracer = Tracer(session, CassetteStore(session), llm=llm)
    context = ExecutionContext(
        run_id=uuid4().hex,
        task=task,
        origin="clean",
        demo_mode=bool(get_settings().BLACKBOX_DEMO_MODE),
        tracer=tracer,
        retriever=get_retriever(),
    )
    return run_agent(task, context)


def _print_run(session: Session, run: Run) -> None:
    console = Console()
    console.print(
        f"[bold]Run {run.run_id}[/bold]  task={run.task_id}  "
        f"outcome={run.outcome}  f1={run.score_f1:.3f}  "
        f"answer={run.final_answer or '-'}"
    )
    table = Table(show_lines=False)
    table.add_column("#", justify="right")
    table.add_column("Step")
    table.add_column("Type")
    table.add_column("Deps")
    table.add_column("Output")
    table.add_column("Cache")
    table.add_column("Error")
    for step in get_steps(session, run.run_id):
        table.add_row(
            str(step.idx),
            step.step_key,
            step.type,
            ", ".join(step.deps) or "-",
            step.output_text,
            "hit" if step.cache_hit else "miss",
            step.error or "",
        )
    console.print(table)


@run_app.command("clean")
def run_clean(
    task_id: str | None = typer.Option(None, "--task-id"),
    all_tasks: bool = typer.Option(False, "--all"),
    limit: int = typer.Option(20, min=1),
) -> None:
    if (task_id is None) == (not all_tasks):
        raise typer.BadParameter("Specify exactly one of --task-id or --all")

    init_db()
    llm = _llm_client()
    with get_session() as session:
        if task_id is not None:
            task = get_task(session, task_id)
            if task is None:
                raise typer.BadParameter(f"Unknown task id: {task_id}")
            _print_run(session, _execute_clean(session, task, llm))
            return

        completed_task_ids = set(
            session.exec(
                select(Run.task_id).where(
                    Run.origin == "clean", Run.outcome.in_(("pass", "fail"))
                )
            ).all()
        )
        pending = [
            task
            for task in list_tasks(session)
            if task.task_id not in completed_task_ids
        ][:limit]
        runs = [_execute_clean(session, task, llm) for task in pending]
        completed = [run for run in runs if run.outcome in {"pass", "fail"}]
        errors = len(runs) - len(completed)
        passed = sum(run.outcome == "pass" for run in completed)
        pass_rate = passed / len(completed) if completed else 0.0
        avg_steps = (
            sum(run.n_steps for run in completed) / len(completed) if completed else 0.0
        )
        typer.echo(
            f"Attempted {len(runs)} clean runs; completed {len(completed)}; "
            f"errors {errors}; skipped {len(completed_task_ids)} existing; "
            f"pass rate {pass_rate:.1%}; avg steps {avg_steps:.2f}."
        )


@run_app.command("show")
def run_show(run_id: str) -> None:
    init_db()
    with get_session() as session:
        run = get_run(session, run_id)
        if run is None:
            raise typer.BadParameter(f"Unknown run id: {run_id}")
        _print_run(session, run)


@faults_app.command("list-targets")
def faults_list_targets(task_id: str = typer.Option(..., "--task-id")) -> None:
    init_db()
    with get_session() as session:
        task = get_task(session, task_id)
        if task is None:
            raise typer.BadParameter(f"Unknown task id: {task_id}")
        clean_run = latest_clean_run(session, task_id)
        if clean_run is None:
            raise typer.BadParameter(f"Task has no passing clean run: {task_id}")
        table = Table("Fault type", "Step")
        for fault_type, step_key in applicable_targets(clean_run):
            table.add_row(fault_type, step_key)
        Console().print(table)


@faults_app.command("inject")
def faults_inject(
    task_id: str = typer.Option(..., "--task-id"),
    fault_type: str = typer.Option(..., "--type"),
    step_key: str = typer.Option(..., "--step"),
    seed: int = typer.Option(42, "--seed"),
) -> None:
    init_db()
    with get_session() as session:
        task = get_task(session, task_id)
        if task is None:
            raise typer.BadParameter(f"Unknown task id: {task_id}")
    try:
        run = run_with_fault(task, fault_type, step_key, seed)
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error
    with get_session() as session:
        _print_run(session, run)


def _parse_replay_overrides(
    set_values: list[str], regenerate_keys: list[str]
) -> dict[str, Override]:
    overrides = {key: Override(kind="regenerate") for key in regenerate_keys}
    for value in set_values:
        if "=" not in value:
            raise typer.BadParameter("--set must use KEY=path/to/output.json")
        key, raw_path = value.split("=", 1)
        if not key or not raw_path:
            raise typer.BadParameter("--set must use KEY=path/to/output.json")
        if key in overrides:
            raise typer.BadParameter(f"Duplicate override for step: {key}")
        try:
            output = json.loads(Path(raw_path).read_text())
        except (OSError, json.JSONDecodeError) as error:
            raise typer.BadParameter(
                f"Cannot read override {raw_path}: {error}"
            ) from error
        if not isinstance(output, dict):
            raise typer.BadParameter(
                f"Override output must be a JSON object: {raw_path}"
            )
        overrides[key] = Override(kind="set_output", output=output)
    return overrides


@app.command("replay")
def replay_command(
    run_id: str,
    set_values: Annotated[
        list[str] | None, typer.Option("--set", metavar="KEY=FILE")
    ] = None,
    regenerate_keys: Annotated[
        list[str] | None, typer.Option("--regen", metavar="KEY")
    ] = None,
    freeze_before_idx: Annotated[
        int | None, typer.Option("--freeze", min=0, metavar="K")
    ] = None,
) -> None:
    overrides = _parse_replay_overrides(set_values or [], regenerate_keys or [])
    try:
        run = replay_run(run_id, overrides, freeze_before_idx)
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error

    console = Console()
    reused_percent = run.n_reused / run.n_steps if run.n_steps else 0.0
    console.print(
        f"[bold green]Replay {run.run_id}[/bold green]  "
        f"outcome=[bold]{run.outcome}[/bold]  "
        f"[cyan]reused {run.n_reused}/{run.n_steps} ({reused_percent:.0%})[/cyan]  "
        f"executed {run.n_executed}  tokens saved {run.tokens_saved:,}"
    )


@app.command("compare")
def compare_command(run_a_id: str, run_b_id: str) -> None:
    init_db()
    with get_session() as session:
        run_a = get_run(session, run_a_id)
        run_b = get_run(session, run_b_id)
        if run_a is None:
            raise typer.BadParameter(f"Unknown run id: {run_a_id}")
        if run_b is None:
            raise typer.BadParameter(f"Unknown run id: {run_b_id}")
        comparison = compare_runs(run_a, run_b)

    console = Console()
    console.print(
        f"[bold]Outcome[/bold] {comparison['summary']['outcome']}  "
        f"first divergence: [yellow]{comparison['first_divergence'] or 'none'}[/yellow]"
    )
    table = Table("Step", "Status", "Text diff")
    for row in comparison["rows"]:
        diff = " ".join(row["text_diff"])
        table.add_row(row["step_key"], row["status"], diff)
    console.print(table)


def _print_label_summary(labels: list[Label], steps_by_run: dict[str, int]) -> None:
    labeled = len(labels)
    verified_rate = (
        sum(label.verified for label in labels) / labeled if labeled else 0.0
    )
    injection_labels = [
        label for label in labels if label.matches_injection is not None
    ]
    matches_rate = (
        sum(bool(label.matches_injection) for label in injection_labels)
        / len(injection_labels)
        if injection_labels
        else None
    )
    avg_replays = sum(label.n_replays for label in labels) / labeled if labeled else 0.0
    avg_steps = (
        sum(steps_by_run[label.run_id] for label in labels) / labeled
        if labeled
        else 0.0
    )
    ratio = avg_replays / avg_steps if avg_steps else 0.0
    matches_text = f"{matches_rate:.1%}" if matches_rate is not None else "n/a"
    Console().print(
        f"[bold]Labeled {labeled}[/bold]; verified {verified_rate:.1%}; "
        f"matches_injection {matches_text}; avg replays/label {avg_replays:.2f} "
        f"vs avg steps {avg_steps:.2f} ([cyan]{ratio:.2f}x[/cyan])."
    )


@label_app.command("faults")
def label_faults(limit: int = typer.Option(20, min=1)) -> None:
    init_db()
    with get_session() as session:
        statement = (
            select(Run)
            .join(Fault, Fault.run_id == Run.run_id)
            .outerjoin(Label, Label.run_id == Run.run_id)
            .where(Run.outcome == "fail", Label.run_id.is_(None))
            .order_by(Run.created_at)
            .limit(limit)
        )
        runs = list(session.exec(statement).all())
    steps_by_run = {run.run_id: run.n_steps for run in runs}
    labels: list[Label] = []
    with Progress() as progress:
        task = progress.add_task("Labeling fault runs", total=len(runs))
        for run in runs:
            label = label_fault_run(run.run_id)
            if label is not None:
                labels.append(label)
            progress.advance(task)
    _print_label_summary(labels, steps_by_run)


@label_app.command("organic")
def label_organic(limit: int = typer.Option(60, min=1)) -> None:
    init_db()
    with get_session() as session:
        statement = (
            select(Run)
            .outerjoin(Fault, Fault.run_id == Run.run_id)
            .outerjoin(Label, Label.run_id == Run.run_id)
            .where(
                Run.origin == "clean",
                Run.outcome == "fail",
                Fault.run_id.is_(None),
                Label.run_id.is_(None),
            )
            .order_by(Run.created_at)
            .limit(limit)
        )
        runs = list(session.exec(statement).all())
    steps_by_run = {run.run_id: run.n_steps for run in runs}
    labels: list[Label] = []
    with Progress() as progress:
        task = progress.add_task("Labeling organic runs", total=len(runs))
        for run in runs:
            label = label_organic_run(run.run_id)
            if label is not None:
                labels.append(label)
            progress.advance(task)
    _print_label_summary(labels, steps_by_run)


def _run_generation(stage: Stage, limit_tasks: int | None) -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
        handlers=[RichHandler(show_time=False, show_path=False)],
    )
    try:
        DataGenerationPipeline().run(stage, limit_tasks)
    except KeyboardInterrupt:
        raise typer.Exit(130) from None


@generate_app.command("all")
def generate_all(
    limit_tasks: int | None = typer.Option(None, "--limit-tasks", min=1),
) -> None:
    _run_generation("all", limit_tasks)


@generate_app.command("clean")
def generate_clean(
    limit_tasks: int | None = typer.Option(None, "--limit-tasks", min=1),
) -> None:
    _run_generation("clean", limit_tasks)


@generate_app.command("faults")
def generate_faults(
    limit_tasks: int | None = typer.Option(None, "--limit-tasks", min=1),
) -> None:
    _run_generation("faults", limit_tasks)


@generate_app.command("label")
def generate_label(
    limit_tasks: int | None = typer.Option(None, "--limit-tasks", min=1),
) -> None:
    _run_generation("label", limit_tasks)


@generate_app.command("organic")
def generate_organic(
    limit_tasks: int | None = typer.Option(None, "--limit-tasks", min=1),
) -> None:
    _run_generation("organic", limit_tasks)


@generate_app.command("status")
def generate_status() -> None:
    report = datagen_status()
    write_datagen_report()
    console = Console()
    console.print(
        f"[bold]Tasks[/bold] {report['tasks']}  "
        f"clean {report['clean']['runs']}  "
        f"pass rate {report['clean']['pass_rate']:.1%}"
    )
    fault_table = Table("Fault type", "Runs", "Failure rate")
    for fault_type, values in report["faults"].items():
        fault_table.add_row(
            fault_type,
            str(values["runs"]),
            f"{values['failure_rate']:.1%}",
        )
    console.print(fault_table)
    console.print(
        f"[bold]Labels[/bold] {report['labels']['total']}  "
        f"verified {report['labels']['verified']} "
        f"({report['labels']['verified_rate']:.1%})  "
        f"matches injection {report['labels']['matches_injection']} "
        f"({report['labels']['matches_injection_rate']:.1%})"
    )
    console.print(
        f"Organic labels {report['organic_labels']}  "
        f"cassette hit rate {report['cassette']['hit_rate']:.1%}  "
        f"total tokens {report['total_tokens']:,}"
    )


@features_app.command("build")
def features_build(split: str = typer.Argument("train")) -> None:
    settings = get_settings()
    features, labels, _, _ = build_dataset(split)
    output_path = Path(settings.ARTIFACTS_DIR) / f"features_{split}.parquet"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    features.to_parquet(output_path, index=False)
    positive_rate = float(labels.mean()) if len(labels) else 0.0
    typer.echo(
        f"Wrote {output_path}: shape={features.shape}, positive_rate={positive_rate:.1%}"
    )


@app.command("train")
def train_command() -> None:
    meta = train_model()
    typer.echo(
        f"Trained {meta['version']} on {meta['train_runs']} runs; "
        f"CV Top-1={meta['cv']['top_1']:.3f}, MRR={meta['cv']['mrr']:.3f}."
    )


@app.command("eval")
def eval_command(
    judge_limit: int = typer.Option(120, "--judge-limit", min=0),
    no_lofo: bool = typer.Option(False, "--no-lofo"),
) -> None:
    result = evaluate(judge_limit=judge_limit, lofo=not no_lofo)
    table = Table("Set", "Method", "Top-1", "Top-3", "MRR", "Mean idx error")
    for row in result["tables"]["baselines"]:
        table.add_row(
            str(row["set"]),
            str(row["method"]),
            f"{row['top_1']:.3f}",
            f"{row['top_3']:.3f}",
            f"{row['mrr']:.3f}",
            f"{row['mean_idx_error']:.2f}",
        )
    Console().print(table)


@app.command("diagnose")
def diagnose_command(run_id: str) -> None:
    try:
        result = diagnose(run_id)
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error
    table = Table("Rank", "Step", "Index", "Score")
    for row in result["ranking"]:
        table.add_row(
            str(row["rank"]), str(row["step_key"]), str(row["idx"]), f"{row['score']:.4f}"
        )
    Console().print(table)
    typer.echo(f"Diagnosis latency: {result['latency_ms']:.1f} ms")


@app.command()
def repair() -> None:
    _not_implemented()


@app.command()
def prewarm() -> None:
    _not_implemented()


if __name__ == "__main__":
    app()
