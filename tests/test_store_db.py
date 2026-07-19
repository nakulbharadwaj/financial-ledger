"""Tests for the store connection layer — path resolution, engine, sessions."""

from datetime import UTC, date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from ledger.store.db import DEFAULT_DB_PATH, get_db_path, get_engine, get_session
from ledger.store.models import Account, Base, Categorization, Transaction, utcnow


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


def test_utcnow_is_timezone_aware() -> None:
    assert utcnow().utcoffset() == timedelta(0)


def test_audit_timestamps_round_trip_as_aware_utc(tmp_path: Path) -> None:
    """SQLite drops tzinfo on its own; UTCDateTime must re-attach it.

    Without this, a stored timestamp reads back naive and comparing it against
    an aware `datetime.now(UTC)` raises TypeError.
    """
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

        with get_session(engine) as session:
            created_at = session.get(Account, "acct-1").created_at
            assert created_at.utcoffset() == timedelta(0)
            # The comparison itself is the regression guard.
            assert datetime.now(UTC) - created_at < timedelta(minutes=1)
    finally:
        engine.dispose()


def test_aware_non_utc_input_is_normalized(tmp_path: Path) -> None:
    """A caller passing a non-UTC timestamp must not shift the stored instant."""
    engine = _make_db(tmp_path)
    ist = timezone(timedelta(hours=5, minutes=30))
    supplied = datetime(2026, 1, 15, 12, 0, tzinfo=ist)
    try:
        with get_session(engine) as session:
            session.add(
                Account(
                    id="acct-1",
                    institution="chase",
                    account_type="checking",
                    display_name="Chase Checking",
                    created_at=supplied,
                )
            )
            session.commit()

        with get_session(engine) as session:
            stored = session.get(Account, "acct-1").created_at
            assert stored.utcoffset() == timedelta(0)
            assert stored == supplied  # same instant, expressed in UTC
            assert stored.hour == 6  # 12:00 +05:30 -> 06:30 UTC
            assert stored.minute == 30
    finally:
        engine.dispose()


def test_nullable_timestamp_stays_none(tmp_path: Path) -> None:
    """A current categorization has no superseded_at — None must survive."""
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
                    description="COFFEE",
                    description_normalized="coffee",
                    amount=Decimal("-4.00"),
                    source_file="x.pdf",
                    source_row_hash="hash-cat",
                )
            )
            session.add(
                Categorization(
                    id="cat-1",
                    transaction_id="txn-1",
                    category="discretionary/dining",
                    confidence=0.9,
                    source="rule",
                )
            )
            session.commit()

        with get_session(engine) as session:
            stored = session.get(Categorization, "cat-1")
            assert stored.superseded_at is None
            assert stored.created_at.utcoffset() == timedelta(0)
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
