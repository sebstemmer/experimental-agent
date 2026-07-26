from datetime import UTC, date, datetime
from enum import StrEnum

from sqlmodel import Column, Field, SQLModel, String


class RecurrenceFrequency(StrEnum):
    day = "daily"
    week = "weekly"
    month = "monthly"
    year = "yearly"


class Todo(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    title: str
    recurrence_frequency: RecurrenceFrequency | None = Field(
        default=None, sa_column=Column(String, nullable=True)
    )
    recurrence_interval: int | None = None
    done: bool = False
    due_date: date | None = None
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC).replace(tzinfo=None)
    )
