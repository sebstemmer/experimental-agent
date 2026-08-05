from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from utils.require_env import require_env

load_dotenv()

engine = create_async_engine(require_env("DATABASE_URL"))


def get_database_session() -> AsyncSession:
    return AsyncSession(engine, expire_on_commit=False)


async def create_all_tables_on_start():
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(SQLModel.metadata.create_all)
