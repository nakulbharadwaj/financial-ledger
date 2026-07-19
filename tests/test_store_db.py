"""Tests for the store connection layer — path resolution, engine, sessions."""

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from ledger.store.db import DEFAULT_DB_PATH, get_db_path, get_engine, get_session
from ledger.store.models import Account, Base, Transaction


@pytest.fixture(autouse=True)
def _isolate_from_dotenv(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep tests independent of any real `.env` on the developer's machine."""
    monkeypatch.setattr("ledger.store.db.load_dotenv", lambda *args, **kwargs: None)


def _make_db(tmp_path: Path):
    """Return an engine backed by a fresh, schema-loaded database."""
    engine = get_engine(tmp_path / "ledger.db")
    Base.metadata.create_all(engine)
    return engine


# ---------- path resolution ----------


def test_get_db_path_defaults_when_env_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LEDGER_DB_PATH", raising=False)
    assert get_db_path() == DEFAULT_DB_PATH


def test_get_db_path_reads_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    target = tmp_path / "custom.db"
    monkeypatch.setenv("LEDGER_DB_PATH", str(target))
    assert get_db_path() == target


# ---------- engine ----------


def test_get_engine_creates_missing_parent_dirs(tmp_path: Path) -> None:
    db_path = tmp_path / "nested" / "deeper" / "ledger.db"
    engine = get_engine(db_path)
    try:
        assert db_path.parent.is_dir()
    finally:
        engine.dispose()


def test_get_engine_can_skip_parent_creation(tmp_path: Path) -> None:
    db_path = tmp_path / "absent" / "ledger.db"
    engine = get_engine(db_path, create_parents=False)
    try:
        assert not db_path.parent.exists()
    finally:
        engine.dispose()


def test_get_engine_enables_foreign_key_pragma(tmp_path: Path) -> None:
    """SQLite ignores FKs unless the pragma is set per connection."""
    engine = get_engine(tmp_path / "ledger.db")
    try:
        with engine.connect() as conn:
            assert conn.execute(text("PRAGMA foreign_keys")).scalar() == 1
    finally:
        engine.dispose()


# ---------- sessions ----------


def test_get_session_round_trips_a_transaction(tmp_path: Path) -> None:
    engine = _make_db(tmp_path)
    try:
        with get_session(engine) as session:
            session.add(
                Account(
                    id="acct-1",
                    institution="chase",
                    account_type="checking",
                    display_name="Chase Checking",
                )
            )
            session.add(
                Transaction(
                    id="txn-1",
                    account_id="acct-1",
                    txn_date=date(2026, 1, 15),
                    description="STARBUCKS #1234",
                    description_normalized="starbucks",
                    amount=Decimal("-5.75"),
                    source_file="chase_2026_01.pdf",
                    source_row_hash="hash-1",
                )
            )
            session.commit()

        with get_session(engine) as session:
            stored = session.get(Transaction, "txn-1")
            assert stored is not None
            # Money must survive the round trip as Decimal, not float.
            assert stored.amount == Decimal("-5.75")
            assert stored.account.display_name == "Chase Checking"
    finally:
        engine.dispose()


def test_orphan_transaction_is_rejected(tmp_path: Path) -> None:
    """Data-model invariant #1: no transaction without an account."""
    engine = _make_db(tmp_path)
    try:
        with get_session(engine) as session:
            session.add(
                Transaction(
                    id="txn-orphan",
                    account_id="does-not-exist",
                    txn_date=date(2026, 1, 15),
                    description="ORPHAN",
                    description_normalized="orphan",
                    amount=Decimal("-1.00"),
                    source_file="x.pdf",
                    source_row_hash="hash-orphan",
                )
            )
            with pytest.raises(IntegrityError):
                session.commit()
    finally:
        engine.dispose()


def test_source_row_hash_is_unique(tmp_path: Path) -> None:
    """Data-model invariant #3: the row hash is the idempotency key."""
    engine = _make_db(tmp_path)
    try:
        with get_session(engine) as session:
            session.add(
                Account(
                    id="acct-1",
                    institution="chase",
                    account_type="checking",
                    display_name="Chase Checking",
                )
            )
            session.commit()

        def _txn(txn_id: str) -> Transaction:
            return Transaction(
                id=txn_id,
                account_id="acct-1",
                txn_date=date(2026, 1, 15),
                description="DUPLICATE",
                description_normalized="duplicate",
                amount=Decimal("-2.00"),
                source_file="x.pdf",
                source_row_hash="same-hash",
            )

        with get_session(engine) as session:
            session.add(_txn("txn-a"))
            session.commit()

        with get_session(engine) as session:
            session.add(_txn("txn-b"))
            with pytest.raises(IntegrityError):
                session.commit()
    finally:
        engine.dispose()
