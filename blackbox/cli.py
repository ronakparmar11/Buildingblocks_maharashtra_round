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
from rich.text import Text
from sqlalchemy import func
from sqlmodel import Session, select

from blackbox.agent.agent import run_agent
from blackbox.config import get_settings
from blackbox.corpus.embed import build_embeddings
from blackbox.corpus.hotpot import build_hotpot_corpus
from blackbox.corpus.nimbu import build_nimbu_corpus
from blackbox.corpus.paths import workspace_data_dir
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
from blackbox.incidents.engine import explain_incident, verify_fix
from blackbox.incidents.simulate import run_simulation
from blackbox.labeling.bisect import label_fault_run
from blackbox.labeling.counterfactual import label_organic_run
from blackbox.llm.base import LLMClient
from blackbox.llm.gemini import GeminiLLM
from blackbox.llm.groq import GroqLLM
from blackbox.model.evaluate import evaluate
from blackbox.model.predict import diagnose
from blackbox.model.train import train_model
from blackbox.notify.mailer import Mailer
from blackbox.notify.rules import evaluate_rules
from blackbox.notify.templates import render_email
from blackbox.notify.worker import worker as notification_worker
from blackbox.repair.repair import repair as repair_run
from blackbox.replay.compare import compare as compare_runs
from blackbox.replay.engine import replay as replay_run
from blackbox.sdk.cassette import Cassette as CassetteStore
from blackbox.sdk.context import ExecutionContext, Override
from blackbox.sdk.tracer import Tracer
from blackbox.store.db import get_session, init_db, migrate_database
from blackbox.store.models import (
    Cassette,
    Fault,
    Incident,
    IncidentEvent,
    Label,
    NotificationLog,
    Prediction,
    Run,
    Step,
    Task,
)
from blackbox.store.repo import get_run, get_steps, get_task, list_tasks
from blackbox.workspaces.seed import seed_demo_clients

app = typer.Typer(help="Black Box agent flight recorder.")
db_app = typer.Typer(help="Initialize and inspect the Black Box database.")
corpus_app = typer.Typer(help="Build and search the retrieval corpus.")
run_app = typer.Typer(help="Execute and inspect agent runs.")
faults_app = typer.Typer(help="List and inject realistic agent faults.")
label_app = typer.Typer(help="Label failed runs with counterfactual replay.")
generate_app = typer.Typer(help="Generate clean, fault, and labeled run data.")
features_app = typer.Typer(help="Build leakage-free step feature datasets.")
incidents_app = typer.Typer(help="Inspect and verify business incidents.")
notify_app = typer.Typer(help="Send and inspect SMTP notifications.")
app.add_typer(db_app, name="db")
app.add_typer(corpus_app, name="corpus")
app.add_typer(run_app, name="run")
app.add_typer(faults_app, name="faults")
app.add_typer(label_app, name="label")
app.add_typer(generate_app, name="generate")
app.add_typer(features_app, name="features")
app.add_typer(incidents_app, name="incidents")
app.add_typer(notify_app, name="notify")

TABLES = (Task, Run, Fault, Step, Label, Prediction, Cassette)


def _not_implemented() -> None:
    typer.echo("not implemented yet")


@db_app.command("init")
def db_init() -> None:
    init_db()
    typer.echo("Database initialized.")


@db_app.command("migrate")
def db_migrate() -> None:
    changes, backup_path = migrate_database(Path(get_settings().DB_PATH))
    if backup_path is not None:
        typer.echo(f"Backup: {backup_path}")
    if changes:
        for change in changes:
            typer.echo(f"Changed: {change}")
    else:
        typer.echo("Database is already at schema v2; no changes made.")


@db_app.command("stats")
def db_stats() -> None:
    init_db()
    with get_session() as session:
        for model in TABLES:
            count = session.exec(select(func.count()).select_from(model)).one()
            typer.echo(f"{model.__tablename__}: {count}")


@db_app.command("seed-clients")
def db_seed_clients() -> None:
    counts = seed_demo_clients()
    typer.echo(
        "Seeded {clients} clients, {tasks} tasks, {runs} runs, and "
        "{incidents} incidents.".format(**counts)
    )


@corpus_app.command("build")
def corpus_build(
    workspace: str = typer.Option("hotpot", "--workspace"),
    force: bool = typer.Option(False, "--force"),
) -> None:
    if workspace not in {"hotpot", "nimbu"}:
        raise typer.BadParameter("Workspace must be 'hotpot' or 'nimbu'")
    settings = get_settings()
    data_dir = workspace_data_dir(settings, workspace)
    outputs = [
        data_dir / "passages.jsonl",
        data_dir / "embeddings.npy",
        data_dir / "pid_index.json",
    ]
    if not force and all(path.exists() for path in outputs):
        typer.echo("Corpus files already exist; use --force to rebuild.")
        return

    if workspace == "nimbu":
        tasks, passages = build_nimbu_corpus(settings)
    else:
        tasks, passages = build_hotpot_corpus(settings)
    build_embeddings(settings, workspace=workspace)
    typer.echo(f"Built {len(tasks)} tasks and {len(passages)} passages.")


@corpus_app.command("search")
def corpus_search(
    query: str,
    workspace: str = typer.Option("hotpot", "--workspace"),
    k: int = typer.Option(3, min=1),
) -> None:
    for result in get_retriever(workspace).search(query, k=k):
        typer.echo(f"{result['score']:.3f}\t{result['title']}\t{result['pid']}")


def _inr(value: int) -> str:
    digits = str(abs(value))
    if len(digits) > 3:
        head, tail = digits[:-3], digits[-3:]
        groups = []
        while head:
            groups.append(head[-2:])
            head = head[:-2]
        digits = f"{','.join(reversed(groups))},{tail}"
    return f"{'-' if value < 0 else ''}₹{digits}"


@incidents_app.command("list")
def incidents_list(workspace: str = typer.Option("nimbu", "--workspace")) -> None:
    init_db()
    with get_session() as session:
        incidents = list(
            session.exec(
                select(Incident)
                .where(Incident.workspace == workspace)
                .order_by(Incident.last_seen.desc())
            ).all()
        )
    table = Table("ID", "Status", "Severity", "Conversations", "Estimated cost", "Title")
    for incident in incidents:
        table.add_row(
            incident.incident_id,
            incident.status,
            incident.severity,
            str(incident.n_runs),
            _inr(incident.est_cost_inr),
            incident.title,
        )
    Console().print(table)


@incidents_app.command("show")
def incidents_show(incident_id: str) -> None:
    init_db()
    with get_session() as session:
        incident = session.get(Incident, incident_id)
        if incident is None:
            raise typer.BadParameter(f"Unknown incident id: {incident_id}")
        events = list(
            session.exec(
                select(IncidentEvent)
                .where(IncidentEvent.incident_id == incident_id)
                .order_by(IncidentEvent.created_at)
            ).all()
        )
        typer.echo(incident.title)
        typer.echo(
            f"{incident.status} · {incident.severity} · {incident.n_runs} conversations · "
            f"{_inr(incident.est_cost_inr)} estimated"
        )
        typer.echo(explain_incident(incident, session))
        typer.echo("Timeline")
        for event in events:
            typer.echo(f"{event.created_at.isoformat()}  {event.text}")


@incidents_app.command("verify")
def incidents_verify(
    incident_id: str, repair_run_id: str = typer.Option(..., "--repair-run")
) -> None:
    result = verify_fix(incident_id, repair_run_id)
    typer.echo(
        f"Fix verified on {result['n_passed']} of {result['n_total']} conversations; "
        f"{result['tokens_saved']:,} tokens saved."
    )


@app.command("simulate")
def simulate(
    workspace: str = typer.Option("nimbu", "--workspace"),
    n: int = typer.Option(30, "--n", min=1),
    failure_rate: float = typer.Option(0.35, "--failure-rate", min=0.0, max=1.0),
    seed: int = typer.Option(7, "--seed"),
) -> None:
    result = run_simulation(workspace, n, failure_rate, seed)
    typer.echo(
        f"Sent {result['sent']}; wrong {result['wrong']}; incidents opened "
        f"{result['incidents_opened']}; emails queued {result['emails_queued']}."
    )


@notify_app.command("test")
def notify_test(to: str = typer.Option(..., "--to")) -> None:
    rendered = render_email("test", {"workspace_name": "Nimbu Living support"})
    row = notification_worker.enqueue("nimbu", "test", [to], rendered)
    notification_worker.wait()
    with get_session() as session:
        stored = session.get(NotificationLog, row.notification_id)
        assert stored is not None
        typer.echo(f"Notification {stored.status}: {stored.notification_id}")


@notify_app.command("status")
def notify_status() -> None:
    settings = get_settings()
    connected, _ = Mailer(settings).check_connection()
    if connected:
        typer.echo(f"Connected to {settings.SMTP_HOST}:{settings.SMTP_PORT} (Mailpit)")
    else:
        typer.echo(
            f"Can't reach the mail server at {settings.SMTP_HOST}:{settings.SMTP_PORT}. "
            "Start Mailpit or update SMTP settings in .env."
        )


@notify_app.command("log")
def notify_log(limit: int = typer.Option(20, "--limit", min=1)) -> None:
    with get_session() as session:
        rows = list(
            session.exec(
                select(NotificationLog)
                .order_by(NotificationLog.created_at.desc())
                .limit(limit)
            ).all()
        )
    table = Table("When", "Kind", "Status", "Subject", "Error")
    for row in rows:
        table.add_row(
            row.created_at.isoformat(),
            row.rule_kind,
            row.status,
            row.subject,
            row.error or "",
        )
    Console().print(table)


@notify_app.command("digest")
def notify_digest(workspace: str = typer.Option("nimbu", "--workspace")) -> None:
    row = evaluate_rules("daily_digest", workspace)
    if row is None:
        typer.echo("Digest not sent.")
        return
    notification_worker.wait()
    with get_session() as session:
        stored = session.get(NotificationLog, row.notification_id)
        assert stored is not None
        typer.echo(f"Digest {stored.status}: {stored.notification_id}")


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
        retriever=get_retriever(task.workspace),
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


def _run_generation(stage: Stage, limit_tasks: int | None, workspace: str) -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
        handlers=[RichHandler(show_time=False, show_path=False)],
    )
    try:
        DataGenerationPipeline(workspace=workspace).run(stage, limit_tasks)
    except KeyboardInterrupt:
        raise typer.Exit(130) from None


@generate_app.command("all")
def generate_all(
    limit_tasks: int | None = typer.Option(None, "--limit-tasks", min=1),
    workspace: str = typer.Option("hotpot", "--workspace"),
) -> None:
    _run_generation("all", limit_tasks, workspace)


@generate_app.command("clean")
def generate_clean(
    limit_tasks: int | None = typer.Option(None, "--limit-tasks", min=1),
    workspace: str = typer.Option("hotpot", "--workspace"),
) -> None:
    _run_generation("clean", limit_tasks, workspace)


@generate_app.command("faults")
def generate_faults(
    limit_tasks: int | None = typer.Option(None, "--limit-tasks", min=1),
    workspace: str = typer.Option("hotpot", "--workspace"),
) -> None:
    _run_generation("faults", limit_tasks, workspace)


@generate_app.command("label")
def generate_label(
    limit_tasks: int | None = typer.Option(None, "--limit-tasks", min=1),
    workspace: str = typer.Option("hotpot", "--workspace"),
) -> None:
    _run_generation("label", limit_tasks, workspace)


@generate_app.command("organic")
def generate_organic(
    limit_tasks: int | None = typer.Option(None, "--limit-tasks", min=1),
    workspace: str = typer.Option("hotpot", "--workspace"),
) -> None:
    _run_generation("organic", limit_tasks, workspace)


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
    repair: bool = typer.Option(False, "--repair"),
) -> None:
    result = evaluate(judge_limit=judge_limit, lofo=not no_lofo, repair=repair)
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
    console = Console()
    console.print(table)
    if repair:
        metrics = result["repair"]
        console.print(
            f"[bold]Repair[/bold] top-1 {metrics['success_top_1']:.1%}  "
            f"top-3 {metrics['success_top_3']:.1%}  "
            f"avg candidates {metrics['avg_candidates']:.2f}  "
            f"avg reused {metrics['avg_pct_reused']:.1%}"
        )


@app.command("diagnose")
def diagnose_command(run_id: str) -> None:
    try:
        result = diagnose(run_id)
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error
    table = Table("Rank", "Step", "Index", "Score", "Likely causes")
    for row in result["ranking"]:
        reasons = Text()
        for index, reason in enumerate(row["reasons"]):
            if index:
                reasons.append("\n")
            reasons.append(f"{reason['text']}\n", style="bold")
            reasons.append(f"{reason['evidence']}\n", style="dim")
            reasons.append(
                f"{reason['feature']}  +{reason['contribution']:.3f}",
                style="cyan",
            )
        table.add_row(
            str(row["rank"]),
            str(row["step_key"]),
            str(row["idx"]),
            f"{row['score']:.4f}",
            reasons,
        )
    console = Console()
    console.print(table)
    console.print(
        f"[bold]Model[/bold] {result['model_version']}  "
        f"[bold]Latency[/bold] {result['latency_ms']:.1f} ms"
    )


@app.command("repair")
def repair_command(
    run_id: str,
    top_k: int = typer.Option(3, "--top-k", min=1, max=3),
    max_workers: int = typer.Option(4, "--max-workers", min=1),
) -> None:
    try:
        result = repair_run(run_id, top_k=top_k, max_workers=max_workers)
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error
    table = Table(
        "Step",
        "Strategy",
        "Outcome",
        "Run",
        "Executed",
        "Reused",
        "Tokens",
    )
    for attempt in result.attempts:
        table.add_row(
            attempt.step_key,
            attempt.strategy,
            attempt.outcome,
            attempt.run_id,
            str(attempt.n_executed),
            f"{attempt.n_reused} ({attempt.pct_reused:.0%})",
            str(attempt.tokens_total),
        )
    console = Console()
    console.print(table)
    if result.repaired:
        console.print(
            f"[bold green]Repaired[/bold green] with {result.winning_step_key}; "
            f"winning run {result.winning_run_id}."
        )
    else:
        console.print("[bold red]No candidate repaired the run.[/bold red]")


@app.command()
def prewarm(
    tasks: Annotated[str, typer.Option("--tasks")],
    faults: Annotated[str, typer.Option("--faults")],
) -> None:
    task_ids = [item.strip() for item in tasks.split(",") if item.strip()]
    fault_specs = [item.strip() for item in faults.split(",") if item.strip()]
    if not task_ids:
        raise typer.BadParameter("--tasks must contain at least one task id")
    if len(task_ids) != len(fault_specs):
        raise typer.BadParameter(
            "--tasks and --faults must contain the same number of items"
        )

    parsed_faults: list[tuple[str, str]] = []
    for spec in fault_specs:
        fault_type, separator, step_key = spec.partition("@")
        if not separator or not fault_type or not step_key:
            raise typer.BadParameter(
                f"Invalid fault '{spec}'; expected TYPE@STEP_KEY"
            )
        parsed_faults.append((fault_type, step_key))

    init_db()
    llm = _llm_client()
    console = Console()
    for task_id, (fault_type, step_key) in zip(
        task_ids, parsed_faults, strict=True
    ):
        with get_session() as session:
            task = get_task(session, task_id)
            if task is None:
                raise typer.BadParameter(f"Unknown task id: {task_id}")
            clean_run = _execute_clean(session, task, llm)
        if clean_run.outcome != "pass":
            raise typer.BadParameter(
                f"Clean run for {task_id} did not pass; choose another demo task"
            )

        fault_run = run_with_fault(
            task,
            fault_type,
            step_key,
            get_settings().SEED,
        )
        if fault_run.outcome != "fail":
            raise typer.BadParameter(
                f"{fault_type}@{step_key} did not fail for {task_id}; "
                "choose another demo scenario"
            )

        diagnosis = diagnose(fault_run.run_id)
        repair = repair_run(fault_run.run_id, top_k=3)
        if not repair.attempts:
            raise typer.BadParameter(
                f"No repair candidates were available for {task_id}"
            )
        with get_session() as session:
            source = get_run(session, fault_run.run_id)
            if source is None:
                raise typer.BadParameter(f"Fault run disappeared: {fault_run.run_id}")
            for attempt in repair.attempts:
                repaired = get_run(session, attempt.run_id)
                if repaired is None:
                    raise typer.BadParameter(
                        f"Repair run disappeared: {attempt.run_id}"
                    )
                compare_runs(source, repaired)

        top_step = diagnosis["ranking"][0]["step_key"]
        status = "repaired" if repair.repaired else "not repaired"
        console.print(
            f"[bold]{task_id}[/bold]  fault={fault_type}@{step_key}  "
            f"top-1={top_step}  attempts={len(repair.attempts)}  {status}"
        )


if __name__ == "__main__":
    app()
