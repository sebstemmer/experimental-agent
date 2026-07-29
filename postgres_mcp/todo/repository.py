from collections.abc import Sequence
from datetime import date

from sqlmodel import col, select, update
from sqlmodel.ext.asyncio.session import AsyncSession

from postgres_mcp.todo.models import RecurrenceFrequency, Todo


async def create_todo(
    session: AsyncSession,
    title: str,
    due_date: date | None,
    recurrence_frequency: RecurrenceFrequency | None = None,
    recurrence_interval: int | None = None,
) -> Todo:
    todo = Todo(
        title=title,
        due_date=due_date,
        recurrence_frequency=recurrence_frequency,
        recurrence_interval=recurrence_interval,
    )
    session.add(todo)
    await session.flush()
    return todo


async def read_all_open_todos(session: AsyncSession) -> Sequence[Todo]:
    result = await session.exec(
        select(Todo).where(col(Todo.done).is_(False)).order_by(col(Todo.due_date).asc())
    )
    return result.all()


async def complete_todo(session: AsyncSession, id: int) -> Todo | None:
    result = await session.exec(
        update(Todo)
        .where(col(Todo.id) == id, col(Todo.done).is_(False))
        .values(done=True)
        .returning(Todo)
    )
    return result.scalars().first()
