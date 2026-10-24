import datetime as dt
from datetime import datetime, timezone

from cryptography.fernet import InvalidToken
from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import TypeDecorator

from .database import Base
from .security import fernet


class EncryptedText(TypeDecorator):
    """Transparent field-level encryption (Fernet) for sensitive free text."""

    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        return None if value is None else fernet.encrypt(value.encode()).decode()

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        try:
            return fernet.decrypt(value.encode()).decode()
        except InvalidToken:
            return "[unreadable]"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120), default="")
    hashed_password: Mapped[str] = mapped_column(String(255))
    opening_balance: Mapped[float] = mapped_column(Float, default=0.0)
    low_balance_threshold: Mapped[float] = mapped_column(Float, default=2000.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    transactions = relationship("Transaction", back_populates="user", cascade="all, delete-orphan")


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    date: Mapped[dt.date] = mapped_column(Date, index=True)
    amount: Mapped[float] = mapped_column(Float)  # always positive
    type: Mapped[str] = mapped_column(String(10))  # "income" | "expense"
    category: Mapped[str] = mapped_column(String(40), default="other")
    description: Mapped[str] = mapped_column(EncryptedText, default="")
    is_recurring: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="transactions")
