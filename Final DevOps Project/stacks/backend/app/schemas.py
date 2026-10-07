"""Pydantic request/response schemas.
Name: Hemang | Enrollment number: 24bcs10209
"""
import re
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

State = Literal["AVAILABLE", "BORROWED"]

# ISBN-10 or ISBN-13, hyphens allowed
_ISBN = re.compile(r"^(?:\d[- ]?){9}[\dXx]$|^(?:\d[- ]?){12}\d$")


def _clean_isbn(value: str) -> str:
    stripped = value.replace("-", "").replace(" ", "")
    if not _ISBN.match(value):
        raise ValueError("isbn must be a valid ISBN-10 or ISBN-13")
    return stripped


class BookCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    author: str = Field(min_length=1, max_length=120)
    isbn: str = Field(min_length=10, max_length=17)

    @field_validator("isbn")
    @classmethod
    def validate_isbn(cls, v: str) -> str:
        return _clean_isbn(v)


class BookUpdate(BaseModel):
    """Used both to correct the catalogue record and to lend or return a copy."""

    title: str | None = Field(default=None, min_length=1, max_length=200)
    author: str | None = Field(default=None, min_length=1, max_length=120)
    state: State | None = None
    borrower: str | None = Field(default=None, max_length=120)
    due_date: date | None = None


class BookOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    author: str
    isbn: str
    state: State
    borrower: str | None
    due_date: date | None
    overdue: bool
    created_at: datetime


class StatsOut(BaseModel):
    total: int
    available: int
    borrowed: int
    overdue: int


class HealthOut(BaseModel):
    status: str
    version: str
    environment: str
