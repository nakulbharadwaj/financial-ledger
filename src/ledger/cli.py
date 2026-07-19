"""CLI entry point. `ledger <subcommand>` after `pip install -e .`."""

import logging
from pathlib import Path

import typer
from rich.console import Console
from sqlalchemy import inspect

from ledger.store.db import get_db_path, get_engine
from ledger.store.models import Base

logger = logging.getLogger(__name__)

app = typer.Typer(
    name="ledger",
    help="Personal finance agent — ingest statements, ask questions, reason over your money.",
    no_args_is_help=True,
)
console = Console()


@app.command()
def init(
    force: bool = typer.Option(
        False, "--force", help="Drop and recreate the database if it already exists."
    ),
) -> None:
    """Initialize the ledger database — create the SQLite schema from store/models.py."""
    db_path = get_db_path()

    if db_path.exists() and not force:
        console.print(f"[yellow]Database already exists at[/yellow] {db_path.resolve()}")
        console.print("Run [bold]ledger init --force[/bold] to drop and recreate it.")
        raise typer.Exit(code=0)

    if db_path.exists() and force:
        logger.warning("dropping existing database", extra={"db_path": str(db_path)})
        db_path.unlink()

    # get_engine() creates parent dirs and enables the FK pragma.
    engine = get_engine(db_path)
    Base.metadata.create_all(engine)
    tables = sorted(inspect(engine).get_table_names())
    engine.dispose()

    logger.info(
        "initialized ledger database",
        extra={"db_path": str(db_path.resolve()), "tables": tables},
    )
    # Plain ASCII output — Windows consoles default to cp1252 and cannot encode
    # glyphs like U+2713, which raises UnicodeEncodeError on write.
    console.print(f"[green]OK[/green] Initialized ledger database at [bold]{db_path.resolve()}[/bold]")
    console.print(f"  Created {len(tables)} tables: {', '.join(tables)}")


@app.command()
def ingest(path: Path) -> None:
    """Ingest a statement file (PDF or CSV) into the ledger."""
    console.print(f"[yellow]TODO:[/yellow] route {path} to the right parser")


@app.command()
def ask(question: str) -> None:
    """Ask a natural-language question about your finances."""
    console.print(f"[yellow]TODO:[/yellow] run agent on: {question!r}")


@app.command()
def eval(dataset: str = "default") -> None:
    """Run the eval harness against a dataset."""
    console.print(f"[yellow]TODO:[/yellow] run evals on dataset={dataset}")


if __name__ == "__main__":
    app()
