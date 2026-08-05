from collections.abc import Sequence

from sqlalchemy.dialects.postgresql import insert
from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from emails.models import Email, ProcessedEmail


async def create_email(session: AsyncSession, email: Email) -> Email | None:
    result = await session.exec(
        insert(Email)
        .values(**email.model_dump(exclude={"id"}))
        .on_conflict_do_nothing()
        .returning(Email)
    )
    return result.scalars().first()


async def read_unprocessed_emails(session: AsyncSession) -> Sequence[Email]:
    result = await session.exec(
        select(Email)
        .outerjoin(ProcessedEmail)
        .where(col(ProcessedEmail.email_id).is_(None))
    )
    return result.all()


async def read_email_by_id(session: AsyncSession, id: int) -> Email | None:
    return await session.get(Email, id)


async def semantic_search_emails(
    session: AsyncSession, query_embedding: list[float], limit: int
) -> Sequence[tuple[Email, ProcessedEmail, float]]:
    distance = col(ProcessedEmail.summary_embedding).cosine_distance(query_embedding)
    result = await session.exec(
        select(Email, ProcessedEmail, (1 - distance).label("similarity"))
        .join(ProcessedEmail)
        .order_by(distance)
        .limit(limit)
    )
    return result.all()


async def create_processed_email(
    session: AsyncSession, processed_email: ProcessedEmail
) -> ProcessedEmail | None:
    result = await session.exec(
        insert(ProcessedEmail)
        .values(**processed_email.model_dump())
        .on_conflict_do_nothing()
        .returning(ProcessedEmail)
    )
    return result.scalars().first()
