"""Database connection setup for the ledger store.

Single source of truth for engine and session creation. The CLI, agent, and
evals all go through here — nothing else should build its own engine, so
connection config (path resolution, the SQLite foreign-key pragma) lives in
exactly one place.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

DEFAULT_DB_PATH = Path("./data/ledger.db")


def get_db_path() -> Path:
    """Resolve the ledger DB path from `LEDGER_DB_PATH` (loading `.env` first)."""
    load_dotenv()
    return Path(os.getenv("LEDGER_DB_PATH", str(DEFAULT_DB_PATH)))


def get_engine(db_path: Path | None = None, *, create_parents: bool = True) -> Engine:
    """Create a SQLite engine with foreign-key enforcement enabled.

    SQLite ignores foreign keys unless `PRAGMA foreign_keys=ON` is set on every
    connection, and the data model relies on FK enforcement (see
    docs/data-model.md, invariant #1).

    Args:
        db_path: Override the configured path. Defaults to `get_db_path()`.
        create_parents: Ensure the parent directory exists before connecting.
    """
    path = Path(db_path) if db_path is not None else get_db_path()
    if create_parents:
        path.parent.mkdir(parents=True, exist_ok=True)

    engine = create_engine(f"sqlite:///{path}")

    @event.listens_for(engine, "connect")
    def _enable_fks(dbapi_connection, _record) -> None:  # type: ignore[no-untyped-def]
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine


@lru_cache(maxsize=1)
def _default_engine() -> Engine:
    """Process-wide engine for the configured DB path."""
    return get_engine()


def get_session(engine: Engine | None = None) -> Session:
    """Return a new Session. Reuses the default engine when none is given.

    The caller owns the session lifecycle — use it as a context manager or
    close it explicitly.
    """
    return Session(bind=engine or _default_engine())
