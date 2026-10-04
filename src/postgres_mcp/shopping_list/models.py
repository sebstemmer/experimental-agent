from datetime import UTC, datetime

from sqlmodel import Field, SQLModel


class ShoppingListItem(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    title: str
    quantity: int = 1
    completed_at: datetime | None = None
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC).replace(tzinfo=None)
    )
