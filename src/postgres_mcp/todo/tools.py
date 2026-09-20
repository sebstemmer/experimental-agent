from datetime import date, datetime
from typing import Annotated
from zoneinfo import ZoneInfo

from dateutil.relativedelta import relativedelta
from fastmcp.exceptions import ToolError
from pydantic import Field as PydanticField

from postgres_mcp.database import get_database_session
from postgres_mcp.mcp_app import mcp
from postgres_mcp.todo.models import RecurrenceFrequency, Todo
from postgres_mcp.todo.repository import complete_todo as complete_todo_in_db
from postgres_mcp.todo.repository import create_todo, read_all_open_todos
from postgres_mcp.todo.repository import delete_todo as delete_todo_in_db
from postgres_mcp.todo.repository import update_todo as update_todo_in_db


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
    next_due: Annotated[
        str | None,
        PydanticField(
            description=(
                "For recurring todos: the due date (YYYY-MM-DD) of the next occurrence. "
                "Pass it whenever the user says when the next one is due; give the resulting date, not a base date. "
                "Example 1 (weekly todo, today 2026-09-20): 'next due in 6 days' -> count 6 days forward from today -> next_due='2026-09-26'. "
                "Example 2 (weekly todo, today 2026-09-20): 'I did it yesterday' -> the next one is due one recurrence after yesterday -> 2026-09-19 + 1 week -> next_due='2026-09-26'. "
                "Must not be in the past."
            )
        ),
    ] = None,
) -> str:
    """Complete a todo. For a recurring todo this also creates the next occurrence,
    due one recurrence after the completed todo's due date unless next_due is given."""
    parsed_next_due = None
    if next_due:
        try:
            parsed_next_due = date.fromisoformat(next_due)
        except ValueError:
            raise ToolError("Invalid next_due format. Please use YYYY-MM-DD.")
        if parsed_next_due < datetime.now(ZoneInfo("Europe/Berlin")).date():
            raise ToolError(
                f"next_due {parsed_next_due} is in the past. Please pass today or a future date."
            )

    async with get_database_session() as session, session.begin():
        todo = await complete_todo_in_db(session, id)
        if todo is None:
            return f"No todo found with ID {id}."

        next_todo = None
        if todo.recurrence_frequency:
            freq = RecurrenceFrequency(todo.recurrence_frequency)
            interval = todo.recurrence_interval or 1
            if parsed_next_due is not None:
                next_due_date = parsed_next_due
            elif todo.due_date is not None:
                next_due_date = todo.due_date + relativedelta(**{f"{freq.name}s": interval})  # type: ignore[arg-type]
            else:
                raise ToolError(
                    "Recurring todo has no due date to compute the next occurrence. Please pass next_due."
                )
            next_todo = await create_todo(
                session,
                todo.title,
                next_due_date,
                todo.recurrence_frequency,
                todo.recurrence_interval,
            )

    result = f"Completed todo {format_todo(todo)}"
    if next_todo is not None:
        result += f". Next one due {next_todo.due_date}"
    return result


@mcp.tool
async def update_todo(
    id: Annotated[int, PydanticField(description="The ID of the todo to update")],
    title: Annotated[
        str | None,
        PydanticField(description="The new title. Omit to leave the title unchanged."),
    ] = None,
    due_date: Annotated[
        str | None,
        PydanticField(
            description="The new due date in YYYY-MM-DD format. Omit to leave the due date unchanged. For a recurring todo this also becomes the base date for the next occurrence."
        ),
    ] = None,
) -> str:
    """Update the title or due date of a todo."""
    if title is None and due_date is None:
        raise ToolError("Nothing to update. Please provide a title or a due_date.")

    parsed_due_date = None
    if due_date:
        try:
            parsed_due_date = date.fromisoformat(due_date)
        except ValueError:
            raise ToolError("Invalid due date format. Please use YYYY-MM-DD.")

    async with get_database_session() as session, session.begin():
        todo = await update_todo_in_db(session, id, title, parsed_due_date)
        if todo is None:
            return f"No open todo found with ID {id}."

        result = f"Updated todo {format_todo(todo)}"

    return result


@mcp.tool
async def delete_todo(
    id: Annotated[int, PydanticField(description="The ID of the todo to delete")],
) -> str:
    """Delete a todo permanently."""
    async with get_database_session() as session, session.begin():
        todo = await delete_todo_in_db(session, id)
        if todo is None:
            return f"No open todo found with ID {id}."

        result = f"Deleted todo {format_todo(todo)}"

    return result
