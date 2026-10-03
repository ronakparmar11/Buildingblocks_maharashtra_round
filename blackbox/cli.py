import typer
from sqlalchemy import func
from sqlmodel import select

from blackbox.store.db import get_session, init_db
from blackbox.store.models import Cassette, Fault, Label, Prediction, Run, Step, Task

app = typer.Typer(help="Black Box agent flight recorder.")
db_app = typer.Typer(help="Initialize and inspect the Black Box database.")
app.add_typer(db_app, name="db")

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


@app.command()
def corpus() -> None:
    _not_implemented()


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
