from pathlib import Path

import typer
from sqlalchemy import func
from sqlmodel import select

from blackbox.config import get_settings
from blackbox.corpus.embed import build_embeddings
from blackbox.corpus.hotpot import build_hotpot_corpus
from blackbox.corpus.retriever import get_retriever
from blackbox.store.db import get_session, init_db
from blackbox.store.models import Cassette, Fault, Label, Prediction, Run, Step, Task

app = typer.Typer(help="Black Box agent flight recorder.")
db_app = typer.Typer(help="Initialize and inspect the Black Box database.")
corpus_app = typer.Typer(help="Build and search the retrieval corpus.")
app.add_typer(db_app, name="db")
app.add_typer(corpus_app, name="corpus")

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


@app.command()
def run() -> None:
    _not_implemented()


@app.command()
def faults() -> None:
    _not_implemented()


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
