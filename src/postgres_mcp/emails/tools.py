from typing import Annotated

from fastmcp.exceptions import ToolError
from langchain_openai import OpenAIEmbeddings
from pydantic import Field as PydanticField

from emails.models import Email, ProcessedEmail
from emails.repository import read_email_by_id, semantic_search_emails
from postgres_mcp.database import get_database_session
from postgres_mcp.mcp_app import mcp

embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

SEARCH_LIMIT = 5


def format_search_result(
    email: Email, processed_email: ProcessedEmail, similarity: float
) -> str:
    sent_at = (
        f"{email.sent_at.strftime('%Y-%m-%d %H:%M')} UTC"
        if email.sent_at
        else "unknown date"
    )
    return (
        f"[id: {email.id}] {sent_at} - from {email.sender} "
        f"(similarity: {similarity:.3f})\n"
        f"Subject: {email.subject}\n"
        f"{processed_email.summary}"
    )


@mcp.tool
async def search_emails(
    query: Annotated[
        str,
        PydanticField(
            description=(
                "A self-contained search query describing what to look for. "
                "Resolve references from the conversation first - do not pass "
                "phrases like 'that order', but the concrete thing meant."
            )
        ),
    ],
) -> str:
    """Search the user's emails by meaning and return the most relevant summaries."""
    query_embedding = await embeddings.aembed_query(query)

    async with get_database_session() as session:
        results = await semantic_search_emails(session, query_embedding, SEARCH_LIMIT)

    if not results:
        return "No emails found."

    return "\n\n".join(
        format_search_result(email, processed_email, similarity)
        for email, processed_email, similarity in results
    )


@mcp.tool
async def get_email(
    id: Annotated[
        int,
        PydanticField(
            description="The id of the email, as returned by search_emails."
        ),
    ],
) -> str:
    """Get the full text of a single email. Use when a summary is not enough."""
    async with get_database_session() as session:
        email = await read_email_by_id(session, id)

    if email is None:
        raise ToolError(f"No email found with id {id}.")

    sent_at = (
        f"{email.sent_at.strftime('%Y-%m-%d %H:%M')} UTC" if email.sent_at else "unknown"
    )
    return (
        f"From: {email.sender}\n"
        f"Date: {sent_at}\n"
        f"Subject: {email.subject}\n\n"
        f"{email.text}"
    )
