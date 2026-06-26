"""Smoke tests — verify the package imports and models work."""

from decimal import Decimal
from datetime import date

from ledger import __version__
from ledger.store.models import RawTransaction, AccountType


def test_version() -> None:
    assert __version__ == "0.1.0"


def test_raw_transaction_model() -> None:
    txn = RawTransaction(
        txn_date=date(2026, 1, 15),
        description="STARBUCKS #1234",
        amount=Decimal("-5.75"),
        source_file="chase_2026_01.pdf",
        source_row_index=42,
    )
    assert txn.amount == Decimal("-5.75")
    assert txn.balance_after is None


def test_account_type_enum() -> None:
    assert AccountType.CREDIT_CARD == "credit_card"
