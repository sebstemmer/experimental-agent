from datetime import date
from typing import Annotated

from dateutil.relativedelta import relativedelta
from fastmcp.exceptions import ToolError
from pydantic import Field as PydanticField

from postgres_mcp.database import get_database_session
from postgres_mcp.mcp_app import mcp
from postgres_mcp.todo.models import RecurrenceFrequency, Todo
from postgres_mcp.todo.repository import complete_todo as complete_todo_in_db
from postgres_mcp.todo.repository import create_todo, read_all_open_todos


def format_todo(todo: Todo) -> str:
    def get_due_date(todo: Todo):
        return f", {todo.due_date.strftime('%Y-%m-%d')}" if todo.due_date else ""

    def get_recurrence(todo: Todo):
        if not todo.recurrence_frequency:
            return ""
        freq = RecurrenceFrequency(todo.recurrence_frequency)
        interval = todo.recurrence_interval or 1
        if interval == 1:
            return f" ({freq})"
        return f" (every {interval} {freq.name}s)"

    return f"{todo.id}: {todo.title}{get_due_date(todo)}{get_recurrence(todo)}"


@mcp.tool
async def add_todo(
    title: Annotated[str, PydanticField(description="The title of the todo to create")],
    due_date: Annotated[
        str | None,
        PydanticField(
            description="The due date of the todo to create, in YYYY-MM-DD format"
        ),
    ] = None,
    recurrence_frequency: Annotated[
        RecurrenceFrequency | None,
        PydanticField(
            description="The repeat unit for a recurring todo. One of: 'daily', 'weekly', 'monthly', 'yearly'. Combine with recurrence_interval for multiples (e.g. 'daily' + 3 = every 3 days). Omit entirely for a one-time todo."
        ),
    ] = None,
    recurrence_interval: Annotated[
        int | None,
        PydanticField(
            description="Repeat every N units of the frequency (e.g. 2 with weekly = every 2 weeks). Defaults to 1 when a frequency is set."
        ),
    ] = None,
) -> str:
    """Add a new todo."""
    parsed_due_date = None
    if due_date:
        try:
            parsed_due_date = date.fromisoformat(due_date)
        except ValueError:
            raise ToolError("Invalid due date format. Please use YYYY-MM-DD.")

    if recurrence_frequency:
        if parsed_due_date is None:
            raise ToolError("Recurring todos need a due date. Please provide due_date.")
        if recurrence_interval is None:
            recurrence_interval = 1

    async with get_database_session() as session, session.begin():
        todo = await create_todo(
            session,
            title,
            parsed_due_date,
            recurrence_frequency,
            recurrence_interval,
        )

    return f"Created todo {format_todo(todo)}"


@mcp.tool
async def get_all_open_todos() -> str:
    """Get all open todos."""
    async with get_database_session() as session:
        todos = await read_all_open_todos(session)

    return f"Open todos: {', '.join([format_todo(todo) for todo in todos])}"


@mcp.tool
async def complete_todo(
    id: Annotated[int, PydanticField(description="The ID of the todo to complete")],
    next_start: Annotated[
        str | None,
        PydanticField(
            description="For recurring todos: base date (YYYY-MM-DD) for the next occurrence. Defaults to the completed todo's due date. Pass today's date to reschedule the next occurrence from now."
        ),
    ] = None,
) -> str:
    """Complete a todo."""
    parsed_next_start = None
    if next_start:
        try:
            parsed_next_start = date.fromisoformat(next_start)
        except ValueError:
            raise ToolError("Invalid next_start format. Please use YYYY-MM-DD.")

    async with get_database_session() as session, session.begin():
        todo = await complete_todo_in_db(session, id)
        if todo is None:
            return f"No todo found with ID {id}."

        next_todo = None
        if todo.recurrence_frequency:
            freq = RecurrenceFrequency(todo.recurrence_frequency)
            interval = todo.recurrence_interval or 1
            anchor = parsed_next_start or todo.due_date
            if anchor is None:
                raise ToolError(
                    "Recurring todo has no due date to compute the next occurrence."
                )
            next_due = anchor + relativedelta(**{f"{freq.name}s": interval})  # type: ignore[arg-type]
            next_todo = await create_todo(
                session,
                todo.title,
                next_due,
                todo.recurrence_frequency,
                todo.recurrence_interval,
            )

    result = f"Completed todo {format_todo(todo)}"
    if next_todo is not None:
        result += f". Next one due {next_todo.due_date}"
    return result
