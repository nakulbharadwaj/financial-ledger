"""Canonical ledger schema. The contract between ingest and everything downstream.

See docs/data-model.md for narrative description.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field
from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class AccountType(StrEnum):
    CHECKING = "checking"
    SAVINGS = "savings"
    CREDIT_CARD = "credit_card"
    BROKERAGE = "brokerage"
    LOAN = "loan"


class CategorizationSource(StrEnum):
    RULE = "rule"
    LLM = "llm"
    USER = "user"


# ---------- SQLAlchemy models (storage layer) ----------


class Base(DeclarativeBase):
    pass


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    institution: Mapped[str] = mapped_column(String, index=True)
    account_type: Mapped[str] = mapped_column(String)
    display_name: Mapped[str] = mapped_column(String)
    account_number_last4: Mapped[str | None] = mapped_column(String(4), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    transactions: Mapped[list[Transaction]] = relationship(back_populates="account")


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"), index=True)
    txn_date: Mapped[date] = mapped_column(Date, index=True)
    description: Mapped[str] = mapped_column(String)
    description_normalized: Mapped[str] = mapped_column(String, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(15, 2))
    balance_after: Mapped[Decimal | None] = mapped_column(Numeric(15, 2), nullable=True)
    source_file: Mapped[str] = mapped_column(String)
    source_row_hash: Mapped[str] = mapped_column(String, unique=True, index=True)
    ingested_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    account: Mapped[Account] = relationship(back_populates="transactions")
    categorizations: Mapped[list[Categorization]] = relationship(back_populates="transaction")


class Categorization(Base):
    __tablename__ = "categorizations"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    transaction_id: Mapped[str] = mapped_column(ForeignKey("transactions.id"), index=True)
    category: Mapped[str] = mapped_column(String, index=True)
    subcategory: Mapped[str | None] = mapped_column(String, nullable=True)
    confidence: Mapped[float] = mapped_column()
    source: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    superseded_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    transaction: Mapped[Transaction] = relationship(back_populates="categorizations")


# ---------- Pydantic models (cross-layer contracts) ----------


class RawTransaction(BaseModel):
    """Output of an ingest parser. The contract between parsers and the store."""

    txn_date: date
    description: str
    amount: Decimal = Field(description="Negative = outflow, positive = inflow.")
    balance_after: Decimal | None = None
    source_file: str
    source_row_index: int = Field(description="Used to compute the idempotency hash.")


class CategorizationResult(BaseModel):
    """Output of the categorization step."""

    transaction_id: str
    category: str
    subcategory: str | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    source: Literal["rule", "llm", "user"]
    reasoning: str | None = Field(default=None, description="For LLM-sourced categorizations.")
