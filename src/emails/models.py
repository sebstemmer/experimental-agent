from datetime import UTC, datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import Column
from sqlmodel import Field, SQLModel


class Email(SQLModel, table=True):
    __tablename__ = "emails"  # type: ignore
    id: int | None = Field(default=None, primary_key=True)
    message_id: str = Field(index=True, unique=True)
    sender: str
    subject: str | None = None
    sent_at: datetime | None = None
    text: str | None = None
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC).replace(tzinfo=None)
    )


class ProcessedEmail(SQLModel, table=True):
    __tablename__ = "processed_emails"  # type: ignore
    email_id: int = Field(foreign_key="emails.id", primary_key=True)
    summary: str
    summary_embedding: list[float] = Field(
        sa_column=Column(Vector(1536), nullable=False)
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC).replace(tzinfo=None)
    )
