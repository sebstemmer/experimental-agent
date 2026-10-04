from typing import Annotated

from pydantic import Field as PydanticField

from postgres_mcp.database import get_database_session
from postgres_mcp.mcp_app import mcp
from postgres_mcp.shopping_list.models import ShoppingListItem
from postgres_mcp.shopping_list.repository import complete_items as complete_items_in_db
from postgres_mcp.shopping_list.repository import create_item, read_all_open_items
from postgres_mcp.shopping_list.repository import delete_item as delete_item_in_db


def format_item(item: ShoppingListItem) -> str:
    return f"{item.id}: {item.quantity}x {item.title}"


@mcp.tool
async def add_shopping_list_item(
    title: Annotated[
        str, PydanticField(description="The name of the item to buy, e.g. 'Milk'")
    ],
    quantity: Annotated[
        int | None,
        PydanticField(
            description="How many units to buy. Only pass this if the user explicitly states an amount; omit it otherwise (defaults to 1).",
            ge=1,
        ),
    ] = None,
) -> str:
    """Add an item to the shopping list."""
    async with get_database_session() as session, session.begin():
        item = await create_item(session, title, quantity)

    return f"Added shopping list item {format_item(item)}"


@mcp.tool
async def get_all_open_shopping_list_items() -> str:
    """Get all items on the shopping list that are not yet bought."""
    async with get_database_session() as session:
        items = await read_all_open_items(session)

    return f"Open shopping list items: {', '.join([format_item(item) for item in items])}"


@mcp.tool
async def complete_shopping_list_items(
    ids: Annotated[
        list[int],
        PydanticField(
            description="The IDs of the shopping list items to mark as bought, e.g. [1, 4, 5]. Pass a single ID for one item."
        ),
    ],
) -> str:
    """Mark one or more shopping list items as bought."""
    async with get_database_session() as session, session.begin():
        items = await complete_items_in_db(session, ids)

    found_ids = {item.id for item in items}
    missing = [id for id in ids if id not in found_ids]

    result = f"Completed shopping list items: {', '.join([format_item(item) for item in items])}"
    if missing:
        result += f". No open item found with ID: {', '.join(map(str, missing))}"
    return result


@mcp.tool
async def delete_shopping_list_item(
    id: Annotated[
        int, PydanticField(description="The ID of the shopping list item to delete")
    ],
) -> str:
    """Delete a shopping list item permanently."""
    async with get_database_session() as session, session.begin():
        item = await delete_item_in_db(session, id)
        if item is None:
            return f"No open shopping list item found with ID {id}."

        result = f"Deleted shopping list item {format_item(item)}"

    return result
