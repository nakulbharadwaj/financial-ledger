"""CLI entry point. `ledger <subcommand>` after `pip install -e .`."""

from pathlib import Path

import typer
from rich.console import Console

app = typer.Typer(
    name="ledger",
    help="Personal finance agent — ingest statements, ask questions, reason over your money.",
    no_args_is_help=True,
)
console = Console()


@app.command()
def init() -> None:
    """Initialize the ledger database."""
    console.print("[yellow]TODO:[/yellow] create SQLite schema from store/models.py")


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
