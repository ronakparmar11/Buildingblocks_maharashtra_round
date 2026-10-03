import typer

app = typer.Typer(help="Black Box agent flight recorder.")


def _not_implemented() -> None:
    typer.echo("not implemented yet")


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
