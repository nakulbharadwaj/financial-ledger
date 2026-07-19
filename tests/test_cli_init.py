"""Tests for `ledger init`."""

from pathlib import Path

import pytest
from sqlalchemy import inspect
from typer.testing import CliRunner

from ledger.cli import app
from ledger.store.db import get_engine, get_session
from ledger.store.models import Account

runner = CliRunner()

EXPECTED_TABLES = {"accounts", "transactions", "categorizations"}


@pytest.fixture(autouse=True)
def _isolate_from_dotenv(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep tests independent of any real `.env` on the developer's machine."""
    monkeypatch.setattr("ledger.store.db.load_dotenv", lambda *args, **kwargs: None)


@pytest.fixture
def db_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point the CLI at a throwaway database under a not-yet-created directory."""
    path = tmp_path / "data" / "ledger.db"
    monkeypatch.setenv("LEDGER_DB_PATH", str(path))
    return path


def _seed_account(path: Path) -> None:
    """Write a marker row so we can tell whether the DB was recreated."""
    engine = get_engine(path)
    try:
        with get_session(engine) as session:
            session.add(
                Account(
                    id="marker",
                    institution="chase",
                    account_type="checking",
                    display_name="Marker",
                )
            )
            session.commit()
    finally:
        engine.dispose()


def _has_account(path: Path, account_id: str) -> bool:
    engine = get_engine(path)
    try:
        with get_session(engine) as session:
            return session.get(Account, account_id) is not None
    finally:
        engine.dispose()


def test_init_creates_database_and_schema(db_path: Path) -> None:
    result = runner.invoke(app, ["init"])

    assert result.exit_code == 0, result.output
    assert db_path.exists()

    engine = get_engine(db_path)
    try:
        assert set(inspect(engine).get_table_names()) >= EXPECTED_TABLES
    finally:
        engine.dispose()


def test_init_creates_parent_directory(db_path: Path) -> None:
    assert not db_path.parent.exists()

    result = runner.invoke(app, ["init"])

    assert result.exit_code == 0, result.output
    assert db_path.parent.is_dir()


def test_init_reports_absolute_path_and_table_count(db_path: Path) -> None:
    result = runner.invoke(app, ["init"])

    assert result.exit_code == 0, result.output
    # Rich may hard-wrap the path across lines, so compare on collapsed output.
    collapsed = "".join(result.output.split())
    assert str(db_path.resolve()).replace(" ", "") in collapsed
    assert "3 tables" in result.output


def test_init_output_is_console_encodable(db_path: Path) -> None:
    """Windows consoles default to cp1252 — non-ASCII glyphs crash on write."""
    result = runner.invoke(app, ["init"])

    assert result.exit_code == 0, result.output
    result.output.encode("cp1252")


def test_init_is_a_no_op_when_database_exists(db_path: Path) -> None:
    runner.invoke(app, ["init"])
    _seed_account(db_path)

    result = runner.invoke(app, ["init"])

    assert result.exit_code == 0, result.output
    assert "already exists" in result.output
    assert _has_account(db_path, "marker"), "existing data must not be destroyed"


def test_init_force_recreates_the_database(db_path: Path) -> None:
    runner.invoke(app, ["init"])
    _seed_account(db_path)

    result = runner.invoke(app, ["init", "--force"])

    assert result.exit_code == 0, result.output
    assert not _has_account(db_path, "marker"), "--force should drop existing data"

    engine = get_engine(db_path)
    try:
        assert set(inspect(engine).get_table_names()) >= EXPECTED_TABLES
    finally:
        engine.dispose()
