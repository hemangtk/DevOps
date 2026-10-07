"""SQLAlchemy ORM models.
Name: Hemang | Enrollment number: 24bcs10209
"""
from datetime import date, datetime, timezone

from sqlalchemy import Date, DateTime, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Book(Base):
    """One physical copy on the shelf.

    `state` is only ever AVAILABLE or BORROWED. "Overdue" is deliberately NOT
    stored: it is derived from due_date, so a loan becomes overdue by the
    passage of time rather than by somebody remembering to run an update.
    """

    __tablename__ = "books"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    author: Mapped[str] = mapped_column(String(120), nullable=False)
    isbn: Mapped[str] = mapped_column(String(17), nullable=False, unique=True, index=True)
    state: Mapped[str] = mapped_column(String(16), default="AVAILABLE", nullable=False)
    borrower: Mapped[str | None] = mapped_column(String(120), nullable=True)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    @property
    def overdue(self) -> bool:
        return (
            self.state == "BORROWED"
            and self.due_date is not None
            and self.due_date < date.today()
        )
