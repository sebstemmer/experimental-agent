from collections.abc import Sequence
from datetime import UTC, datetime

from sqlmodel import col, delete, select, update
from sqlmodel.ext.asyncio.session import AsyncSession

from postgres_mcp.shopping_list.models import ShoppingListItem


async def create_item(
    session: AsyncSession, title: str, quantity: int | None
) -> ShoppingListItem:
    item = ShoppingListItem(title=title)
    if quantity is not None:
        item.quantity = quantity
    session.add(item)
    await session.flush()
    return item


async def read_all_open_items(session: AsyncSession) -> Sequence[ShoppingListItem]:
    result = await session.exec(
        select(ShoppingListItem)
        .where(col(ShoppingListItem.completed_at).is_(None))
        .order_by(col(ShoppingListItem.created_at).asc())
    )
    return result.all()


async def complete_items(
    session: AsyncSession, ids: list[int]
) -> Sequence[ShoppingListItem]:
    result = await session.exec(
        update(ShoppingListItem)
        .where(
            col(ShoppingListItem.id).in_(ids),
            col(ShoppingListItem.completed_at).is_(None),
        )
        .values(completed_at=datetime.now(UTC).replace(tzinfo=None))
        .returning(ShoppingListItem)
    )
    return result.scalars().all()


async def delete_item(session: AsyncSession, id: int) -> ShoppingListItem | None:
    result = await session.exec(
        delete(ShoppingListItem)
        .where(
            col(ShoppingListItem.id) == id,
            col(ShoppingListItem.completed_at).is_(None),
        )
        .returning(ShoppingListItem)
    )
    return result.scalars().first()
