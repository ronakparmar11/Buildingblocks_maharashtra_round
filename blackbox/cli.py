from pathlib import Path
from uuid import uuid4

import typer
from rich.console import Console
from rich.table import Table
from sqlalchemy import func
from sqlmodel import Session, select

from blackbox.agent.agent import run_agent
from blackbox.config import get_settings
from blackbox.corpus.embed import build_embeddings
from blackbox.corpus.hotpot import build_hotpot_corpus
from blackbox.corpus.retriever import get_retriever
from blackbox.faults.inject import run_with_fault
from blackbox.faults.targets import applicable_targets, latest_clean_run
from blackbox.llm.base import LLMClient
from blackbox.llm.gemini import GeminiLLM
from blackbox.llm.groq import GroqLLM
from blackbox.sdk.cassette import Cassette as CassetteStore
from blackbox.sdk.context import ExecutionContext
from blackbox.sdk.tracer import Tracer
from blackbox.store.db import get_session, init_db
from blackbox.store.models import Cassette, Fault, Label, Prediction, Run, Step, Task
from blackbox.store.repo import get_run, get_steps, get_task, list_tasks

app = typer.Typer(help="Black Box agent flight recorder.")
db_app = typer.Typer(help="Initialize and inspect the Black Box database.")
corpus_app = typer.Typer(help="Build and search the retrieval corpus.")
run_app = typer.Typer(help="Execute and inspect agent runs.")
faults_app = typer.Typer(help="List and inject realistic agent faults.")
app.add_typer(db_app, name="db")
app.add_typer(corpus_app, name="corpus")
app.add_typer(run_app, name="run")
app.add_typer(faults_app, name="faults")

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
            task for task in list_tasks(session) if task.task_id not in completed_task_ids
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


@app.command()
def label() -> None:
    _not_implemented()


@app.command()
def generate() -> None:
    _not_implemented()


@app.command()
def features() -> None:
    _not_implemented()


@app.command()
def train() -> None:
    _not_implemented()


@app.command()
def eval() -> None:
    _not_implemented()


@app.command()
def repair() -> None:
    _not_implemented()


@app.command()
def prewarm() -> None:
    _not_implemented()


if __name__ == "__main__":
    app()
